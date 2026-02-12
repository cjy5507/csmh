#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set

MAX_RETRY_BACKOFF_SEC = 5.0
BASE_RETRY_BACKOFF_SEC = 0.25


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AttemptLog:
    attempt: int
    started_at: str
    ended_at: str
    duration_sec: float
    exit_code: int
    stdout: str
    stderr: str
    error: Optional[str]


@dataclass
class TaskSpec:
    id: str
    command: str
    depends_on: List[str]
    writes: List[str]
    timeout_sec: Optional[int]
    retries: int


@dataclass
class TaskResult:
    id: str
    status: str
    attempts: int
    started_at: Optional[str]
    ended_at: Optional[str]
    duration_sec: float
    exit_code: Optional[int]
    stdout: str
    stderr: str
    error: Optional[str]
    attempt_logs: List[AttemptLog]

    def to_dict(self) -> dict:
        return asdict(self)


class MissionError(Exception):
    pass


def normalize_write_target(target: str) -> str:
    cleaned = target.strip()
    if cleaned.startswith("logical:"):
        return cleaned
    return str(Path(cleaned).expanduser().resolve(strict=False))


def mode_defaults(mode: str) -> dict:
    table = {
        "fast": {"max_concurrency": 6, "default_retries": 0},
        "balanced": {"max_concurrency": 4, "default_retries": 1},
        "strict": {"max_concurrency": 3, "default_retries": 1},
    }
    if mode not in table:
        raise MissionError("mode must be one of: fast, balanced, strict")
    return table[mode]


def run_command(command: str, timeout_sec: Optional[int]) -> AttemptLog:
    started_at = utc_now()
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout_sec,
        )
        exit_code = completed.returncode
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        error = None
    except subprocess.TimeoutExpired as exc:
        exit_code = 124
        stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        error = f"timed out after {timeout_sec}s"
    except Exception as exc:
        exit_code = 1
        stdout = ""
        stderr = ""
        error = str(exc)
    ended = time.perf_counter()
    ended_at = utc_now()
    return AttemptLog(
        attempt=0,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=round(ended - started, 3),
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        error=error,
    )


def execute_task(task: TaskSpec) -> TaskResult:
    max_attempts = max(1, task.retries + 1)
    logs: List[AttemptLog] = []
    first_started: Optional[str] = None
    last_ended: Optional[str] = None
    for i in range(max_attempts):
        attempt_log = run_command(task.command, task.timeout_sec)
        attempt_log.attempt = i + 1
        logs.append(attempt_log)
        if first_started is None:
            first_started = attempt_log.started_at
        last_ended = attempt_log.ended_at
        if attempt_log.exit_code == 0:
            break
        if i < max_attempts - 1:
            delay = min(MAX_RETRY_BACKOFF_SEC, BASE_RETRY_BACKOFF_SEC * (2**i))
            time.sleep(delay)

    final = logs[-1]
    status = "succeeded" if final.exit_code == 0 else "failed"
    total_duration = round(sum(a.duration_sec for a in logs), 3)
    return TaskResult(
        id=task.id,
        status=status,
        attempts=len(logs),
        started_at=first_started,
        ended_at=last_ended,
        duration_sec=total_duration,
        exit_code=final.exit_code,
        stdout=final.stdout,
        stderr=final.stderr,
        error=final.error,
        attempt_logs=logs,
    )


def parse_tasks(mission: dict) -> Dict[str, TaskSpec]:
    mode = mission.get("mode", "balanced")
    defaults = mode_defaults(mode)
    default_timeout = mission.get("default_timeout_sec")
    default_retries = mission.get("default_retries", defaults["default_retries"])

    raw_tasks = mission.get("tasks")
    if not isinstance(raw_tasks, list) or not raw_tasks:
        raise MissionError("mission.tasks must be a non-empty list")

    task_map: Dict[str, TaskSpec] = {}
    for raw in raw_tasks:
        if not isinstance(raw, dict):
            raise MissionError("each task entry must be an object")
        task_id = raw.get("id")
        command = raw.get("command")
        if not isinstance(task_id, str) or not task_id:
            raise MissionError("task.id must be a non-empty string")
        if task_id in task_map:
            raise MissionError(f"duplicate task id: {task_id}")
        if not isinstance(command, str) or not command.strip():
            raise MissionError(f"task.command is required for task: {task_id}")

        depends_on = raw.get("depends_on", [])
        writes = raw.get("writes", [])
        timeout_sec = raw.get("timeout_sec", default_timeout)
        retries = raw.get("retries", default_retries)

        if not isinstance(depends_on, list) or not all(isinstance(x, str) for x in depends_on):
            raise MissionError(f"task.depends_on must be a string list: {task_id}")
        if not isinstance(writes, list) or not all(isinstance(x, str) and x.strip() for x in writes):
            raise MissionError(f"task.writes must be a string list: {task_id}")
        if timeout_sec is not None and (not isinstance(timeout_sec, int) or timeout_sec <= 0):
            raise MissionError(f"task.timeout_sec must be a positive integer: {task_id}")
        if not isinstance(retries, int) or retries < 0:
            raise MissionError(f"task.retries must be an integer >= 0: {task_id}")

        normalized_writes = [normalize_write_target(x) for x in writes]

        task_map[task_id] = TaskSpec(
            id=task_id,
            command=command,
            depends_on=depends_on,
            writes=normalized_writes,
            timeout_sec=timeout_sec,
            retries=retries,
        )

    for task in task_map.values():
        for dep in task.depends_on:
            if dep not in task_map:
                raise MissionError(f"task '{task.id}' depends on unknown task '{dep}'")

    validate_acyclic(task_map)
    return task_map


def validate_acyclic(task_map: Dict[str, TaskSpec]) -> None:
    visiting: Set[str] = set()
    visited: Set[str] = set()

    def dfs(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise MissionError(f"cycle detected at task '{task_id}'")
        visiting.add(task_id)
        for dep in task_map[task_id].depends_on:
            dfs(dep)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in task_map:
        dfs(task_id)


def blocked_result(task_id: str, reason: str) -> TaskResult:
    return TaskResult(
        id=task_id,
        status="blocked",
        attempts=0,
        started_at=None,
        ended_at=None,
        duration_sec=0.0,
        exit_code=None,
        stdout="",
        stderr="",
        error=reason,
        attempt_logs=[],
    )


def dispatch_tasks(task_map: Dict[str, TaskSpec], max_concurrency: int, quiet: bool) -> Dict[str, TaskResult]:
    if max_concurrency <= 0:
        raise MissionError("max_concurrency must be >= 1")

    pending: Dict[str, TaskSpec] = dict(task_map)
    running = {}
    succeeded: Set[str] = set()
    failed: Set[str] = set()
    blocked: Set[str] = set()
    locked_writes: Set[str] = set()
    results: Dict[str, TaskResult] = {}

    pool = ThreadPoolExecutor(max_workers=max_concurrency)
    interrupted = False
    try:
        while pending or running:
            for task_id in list(pending.keys()):
                task = pending[task_id]
                if any(dep in failed or dep in blocked for dep in task.depends_on):
                    reason = "blocked by failed dependency"
                    results[task_id] = blocked_result(task_id, reason)
                    blocked.add(task_id)
                    pending.pop(task_id)
                    if not quiet:
                        print(f"[blocked] {task_id}: {reason}")

            ready: List[TaskSpec] = []
            for task in pending.values():
                if all(dep in succeeded for dep in task.depends_on):
                    ready.append(task)

            ready.sort(key=lambda t: t.id)
            for task in ready:
                if len(running) >= max_concurrency:
                    break
                if set(task.writes) & locked_writes:
                    continue
                future = pool.submit(execute_task, task)
                running[future] = task
                pending.pop(task.id)
                locked_writes.update(task.writes)
                if not quiet:
                    print(f"[start] {task.id}")

            if not running:
                if pending:
                    stuck = ", ".join(sorted(pending.keys()))
                    raise MissionError(f"no runnable tasks remain: {stuck}")
                break

            done, _ = wait(running.keys(), timeout=0.2, return_when=FIRST_COMPLETED)
            if not done:
                continue

            for future in done:
                task = running.pop(future)
                locked_writes.difference_update(task.writes)
                try:
                    result = future.result()
                except Exception as exc:
                    result = TaskResult(
                        id=task.id,
                        status="failed",
                        attempts=0,
                        started_at=None,
                        ended_at=utc_now(),
                        duration_sec=0.0,
                        exit_code=1,
                        stdout="",
                        stderr="",
                        error=f"worker exception: {exc}",
                        attempt_logs=[],
                    )
                results[task.id] = result
                if result.status == "succeeded":
                    succeeded.add(task.id)
                else:
                    failed.add(task.id)
                if not quiet:
                    print(
                        f"[done] {task.id} status={result.status} "
                        f"attempts={result.attempts} duration={result.duration_sec}s"
                    )
    except KeyboardInterrupt as exc:
        interrupted = True
        for future in list(running.keys()):
            future.cancel()
        pool.shutdown(wait=False, cancel_futures=True)
        raise MissionError("interrupted by user") from exc
    finally:
        if not interrupted:
            pool.shutdown(wait=True)

    return results


def parse_phase(spec: Optional[dict], default_timeout: Optional[int]) -> Optional[TaskSpec]:
    if spec is None:
        return None
    if not isinstance(spec, dict):
        raise MissionError("phase definition must be an object")
    command = spec.get("command")
    if not isinstance(command, str) or not command.strip():
        raise MissionError("phase.command must be a non-empty string")
    timeout_sec = spec.get("timeout_sec", default_timeout)
    retries = spec.get("retries", 0)
    if timeout_sec is not None and (not isinstance(timeout_sec, int) or timeout_sec <= 0):
        raise MissionError("phase.timeout_sec must be a positive integer")
    if not isinstance(retries, int) or retries < 0:
        raise MissionError("phase.retries must be an integer >= 0")
    return TaskSpec(
        id="phase",
        command=command,
        depends_on=[],
        writes=[],
        timeout_sec=timeout_sec,
        retries=retries,
    )


def run_phase(name: str, spec: Optional[TaskSpec], quiet: bool) -> Optional[TaskResult]:
    if spec is None:
        return None
    spec.id = name
    if not quiet:
        print(f"[phase:start] {name}")
    result = execute_task(spec)
    if not quiet:
        print(
            f"[phase:done] {name} status={result.status} "
            f"attempts={result.attempts} duration={result.duration_sec}s"
        )
    return result


def run_mission(mission_path: Path, quiet: bool) -> dict:
    mission = json.loads(mission_path.read_text(encoding="utf-8"))
    if not isinstance(mission, dict):
        raise MissionError("mission root must be a JSON object")

    mode = mission.get("mode", "balanced")
    defaults = mode_defaults(mode)
    max_concurrency = mission.get("max_concurrency", defaults["max_concurrency"])
    if not isinstance(max_concurrency, int) or max_concurrency <= 0:
        raise MissionError("max_concurrency must be an integer >= 1")

    default_timeout = mission.get("default_timeout_sec")
    if default_timeout is not None and (not isinstance(default_timeout, int) or default_timeout <= 0):
        raise MissionError("default_timeout_sec must be a positive integer")

    tasks = parse_tasks(mission)

    started_at = utc_now()
    started_perf = time.perf_counter()
    task_results = dispatch_tasks(tasks, max_concurrency=max_concurrency, quiet=quiet)

    failed_or_blocked = [
        task_id
        for task_id, result in task_results.items()
        if result.status in {"failed", "blocked"}
    ]

    integrate_result = None
    verify_result = None
    if not failed_or_blocked:
        integrate = parse_phase(mission.get("integrate"), default_timeout)
        verify = parse_phase(mission.get("verify"), default_timeout)
        integrate_result = run_phase("integrate", integrate, quiet=quiet)
        if integrate_result and integrate_result.status != "succeeded":
            failed_or_blocked.append("integrate")
        else:
            verify_result = run_phase("verify", verify, quiet=quiet)
            if verify_result and verify_result.status != "succeeded":
                failed_or_blocked.append("verify")

    ended_at = utc_now()
    total_duration = round(time.perf_counter() - started_perf, 3)
    status = "succeeded" if not failed_or_blocked else "failed"
    return {
        "mission": {
            "path": str(mission_path),
            "mode": mode,
            "objective": mission.get("objective"),
            "max_concurrency": max_concurrency,
        },
        "status": status,
        "started_at": started_at,
        "ended_at": ended_at,
        "duration_sec": total_duration,
        "failed_or_blocked": failed_or_blocked,
        "tasks": {task_id: result.to_dict() for task_id, result in sorted(task_results.items())},
        "integrate": integrate_result.to_dict() if integrate_result else None,
        "verify": verify_result.to_dict() if verify_result else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CSMH dependency-aware parallel orchestrator. "
            "Input must be a mission JSON file."
        )
    )
    parser.add_argument("mission", help="path to mission JSON")
    parser.add_argument(
        "--report",
        default="csmh-report.json",
        help="output report JSON path (default: csmh-report.json)",
    )
    parser.add_argument("--quiet", action="store_true", help="suppress progress logs")
    args = parser.parse_args()

    mission_path = Path(args.mission)
    if not mission_path.exists():
        print(f"mission file not found: {mission_path}")
        return 2

    try:
        report = run_mission(mission_path, quiet=args.quiet)
    except MissionError as exc:
        print(f"mission error: {exc}")
        return 2
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}")
        return 2

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=True, indent=2), encoding="utf-8")

    print(f"status: {report['status']}")
    print(f"duration_sec: {report['duration_sec']}")
    print(f"report: {report_path}")
    return 0 if report["status"] == "succeeded" else 1


if __name__ == "__main__":
    sys.exit(main())
