#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path
from typing import Optional


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def script_home() -> Path:
    return Path(__file__).resolve().parent


def runtime_root() -> Path:
    local_home = script_home()
    if (local_home / "csmh-orchestrator.py").exists():
        return local_home

    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex")))
    installed = codex_home / "csmh"
    if installed.exists() and (installed / "csmh-orchestrator.py").exists():
        return installed
    return repo_root() / "scripts"


def find_engine() -> Path:
    candidates = [
        runtime_root() / "csmh-orchestrator.py",
        repo_root() / "scripts" / "csmh-orchestrator.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("csmh-orchestrator.py not found")


def find_verify_script() -> Path:
    candidates = [
        runtime_root() / "csmh-verify.sh",
        repo_root() / "scripts" / "csmh-verify.sh",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError("csmh-verify.sh not found")


def find_version() -> str:
    candidates = [
        runtime_root() / "VERSION",
        repo_root() / "VERSION",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text(encoding="utf-8").strip()
    return "0.0.0"


def cmd_init(_args: argparse.Namespace) -> int:
    root = Path.cwd() / ".csmh"
    for name in ["state", "missions", "reports", "logs", "locks"]:
        (root / name).mkdir(parents=True, exist_ok=True)
    cfg = root / "config.json"
    if not cfg.exists():
        cfg.write_text(
            """{
  "default_mode": "balanced",
  "max_concurrency": 4,
  "default_timeout_sec": 300,
  "default_retries": 1
}
""",
            encoding="utf-8",
        )
    print(f"initialized: {root}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    engine = find_engine()
    cmd = [sys.executable, str(engine), args.mission]
    if args.report:
        cmd += ["--report", args.report]
    if args.quiet:
        cmd += ["--quiet"]
    return subprocess.call(cmd)


def _read_active_pid(pid_file: Path) -> Optional[int]:
    if not pid_file.exists():
        return None
    raw = pid_file.read_text(encoding="utf-8").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _process_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cmd_start(args: argparse.Namespace) -> int:
    engine = find_engine()
    state_dir = Path.cwd() / ".csmh" / "state"
    log_dir = Path.cwd() / ".csmh" / "logs"
    report_dir = Path.cwd() / ".csmh" / "reports"
    state_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    pid_file = state_dir / "active.pid"
    old_pid = _read_active_pid(pid_file)
    if old_pid and _process_exists(old_pid):
        print(f"an active mission is already running (pid: {old_pid})")
        return 1

    report = args.report or str(report_dir / "active-report.json")
    log_file = log_dir / "active.log"

    cmd = [sys.executable, str(engine), args.mission, "--report", report]
    if args.quiet:
        cmd.append("--quiet")

    with log_file.open("a", encoding="utf-8") as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)

    pid_file.write_text(str(proc.pid), encoding="utf-8")
    print(f"started mission pid={proc.pid}")
    print(f"log={log_file}")
    print(f"report={report}")
    return 0


def cmd_cancel(_args: argparse.Namespace) -> int:
    pid_file = Path.cwd() / ".csmh" / "state" / "active.pid"
    pid = _read_active_pid(pid_file)
    if not pid:
        print("no active mission pid found")
        return 0

    if _process_exists(pid):
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

        for _ in range(10):
            if not _process_exists(pid):
                break
            import time

            time.sleep(0.1)

        if _process_exists(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        print(f"stopped mission pid={pid}")
    else:
        print("process not running; cleaned stale pid")

    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    mode = args.mode or "parallel"
    if mode != "parallel":
        print(f"unsupported verify mode: {mode}")
        print("supported: parallel")
        return 2

    verify_script = find_verify_script()
    bash = shutil.which("bash")
    if not bash:
        print("bash is required for verify command")
        return 1

    return subprocess.call([bash, str(verify_script), mode])


def cmd_doctor(_args: argparse.Namespace) -> int:
    missing = []
    for dep in ["python3", "bash"]:
        if not shutil.which(dep):
            missing.append(dep)
    if missing:
        for dep in missing:
            print(f"missing dependency: {dep}")
        return 1

    print("ok: required dependencies found")
    print(f"engine: {find_engine()}")
    print(f"codex_home: {Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))}")
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(find_version())
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="CSMH CLI")
    sub = p.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run mission")
    run.add_argument("mission")
    run.add_argument("--report")
    run.add_argument("--quiet", action="store_true")
    run.set_defaults(fn=cmd_run)

    start = sub.add_parser("start", help="Run mission in background")
    start.add_argument("mission")
    start.add_argument("--report")
    start.add_argument("--quiet", action="store_true")
    start.set_defaults(fn=cmd_start)

    cancel = sub.add_parser("cancel", help="Cancel background mission")
    cancel.set_defaults(fn=cmd_cancel)

    init = sub.add_parser("init", help="Initialize .csmh")
    init.set_defaults(fn=cmd_init)

    verify = sub.add_parser("verify", help="Run runtime verification")
    verify.add_argument("mode", nargs="?")
    verify.set_defaults(fn=cmd_verify)

    doctor = sub.add_parser("doctor", help="Check local dependencies")
    doctor.set_defaults(fn=cmd_doctor)

    version = sub.add_parser("version", help="Show version")
    version.set_defaults(fn=cmd_version)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
