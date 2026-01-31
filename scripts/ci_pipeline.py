#!/usr/bin/env python3
"""CourseScope CI helper.

v1.1.31+: legacy UI removed. This script runs the real backend + frontend test
suites and produces `ci_report.json`.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd: str, description: str, *, cwd: Path, timeout: int = 900):
    print(f"\n{'=' * 60}")
    print(f"[RUN] {description}")
    print(f"[CMD] {cmd}")
    print(f"{'=' * 60}")

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        print(f"[FAIL] {description} (timeout after {timeout}s)")
        return False, f"Command timeout after {timeout}s", duration
    except Exception as e:  # pragma: no cover
        duration = time.time() - start_time
        print(f"[FAIL] {description} (error: {e})")
        return False, str(e), duration

    duration = time.time() - start_time
    if result.returncode == 0:
        print(f"[OK] {description} ({duration:.2f}s)")
        return True, result.stdout, duration

    print(f"[FAIL] {description} ({duration:.2f}s)")
    if result.stdout:
        print("STDOUT:\n" + result.stdout)
    if result.stderr:
        print("STDERR:\n" + result.stderr)
    return False, result.stderr or result.stdout, duration


def run_backend_tests(results: list[dict]):
    for cmd, name in [
        ("python -m pytest tests/unit -v", "Backend: pytest tests/unit"),
        ("python -m pytest tests/pytest -v", "Backend: pytest tests/pytest"),
    ]:
        success, _, duration = run_command(cmd, name, cwd=REPO_ROOT)
        results.append({"name": name, "success": success, "duration": duration})


def run_frontend_tests(results: list[dict]):
    frontend_dir = REPO_ROOT / "frontend"
    name = "Frontend: npm test"

    if not frontend_dir.exists():
        results.append({"name": name, "success": False, "duration": 0, "error": "frontend/ not found"})
        return

    if shutil.which("npm") is None:
        results.append({"name": name, "success": False, "duration": 0, "error": "npm not found"})
        return

    lockfile = frontend_dir / "package-lock.json"
    install_primary = "npm ci" if lockfile.exists() else "npm install"

    ok_install, _, dur_install = run_command(install_primary, "Frontend: install", cwd=frontend_dir)
    if not ok_install and install_primary == "npm ci":
        # Windows environments can hit transient file locks during `npm ci`.
        ok_install, _, dur_install = run_command("npm install", "Frontend: install (fallback)", cwd=frontend_dir)
        results.append({"name": "Frontend: install (fallback)", "success": ok_install, "duration": dur_install})
    else:
        results.append({"name": "Frontend: install", "success": ok_install, "duration": dur_install})

    if not ok_install:
        return

    ok_test, _, dur_test = run_command("npm test", name, cwd=frontend_dir)
    results.append({"name": name, "success": ok_test, "duration": dur_test})
    if not ok_test:
        return

    ok_build, _, dur_build = run_command("npm run build", "Frontend: npm run build", cwd=frontend_dir)
    results.append({"name": "Frontend: npm run build", "success": ok_build, "duration": dur_build})


def generate_report(results):
    """Génère un rapport d'exécution"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_duration": sum(r["duration"] for r in results),
        "results": results,
        "summary": {
            "total_tests": len(results),
            "passed": sum(1 for r in results if r['success']),
            "failed": sum(1 for r in results if not r["success"]),
            "success_rate": f"{(sum(1 for r in results if r['success']) / len(results) * 100):.1f}%"
        }
    }
    
    # Sauvegarder le rapport
    report_path = Path("ci_report.json")
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report


def main():
    """Fonction principale d'intégration continue"""
    print(f"\n[CI] START {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = []

    run_backend_tests(results)
    run_frontend_tests(results)
    
    # Générer le rapport
    report = generate_report(results)
    
    # Afficher le résumé
    print(f"\n{'='*80}")
    print("CI REPORT")
    print(f"{'='*80}")
    
    total_duration = report["total_duration"]
    passed = report["summary"]["passed"]
    failed = report["summary"]["failed"]
    success_rate = report["summary"]["success_rate"]
    
    print(f"Total duration: {total_duration:.2f}s")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Success rate: {success_rate}")
    
    if failed > 0:
        print("\nFailed steps:")
        for result in results:
            if not result["success"]:
                print(f"  - {result['name']}")
    
    print("\nReport: ci_report.json")
    
    # Retourner le résultat global
    overall_success = failed == 0
    
    if overall_success:
        print("\n[CI] SUCCESS")
        return True
    print("\n[CI] FAILED")
    return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
