"""The public demo command must work offline, including with inherited settings."""
import os
from pathlib import Path
import subprocess
import sys


def test_demo_script():
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, OPENAI_API_KEY="offline-sentinel", OPENAI_MODEL="offline-sentinel",
               DATA_PATH="nonexistent-catalogue.csv", PYTHONIOENCODING="utf-8")
    result = subprocess.run([sys.executable, str(root / "scripts/demo.py")],
                            cwd=root, env=env, capture_output=True, text=True,
                            encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "❌" not in result.stdout
    assert "Итого:" in result.stdout


def test_demo_script_windows_cp1251_console():
    """Windows consoles/pipes with CP1251 cannot encode emoji; the demo must still pass."""
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, OPENAI_API_KEY="", OPENAI_MODEL="", PYTHONIOENCODING="cp1251")
    result = subprocess.run([sys.executable, str(root / "scripts/demo.py")],
                            cwd=root, env=env, capture_output=True, text=True,
                            encoding="cp1251", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "[FAIL]" not in result.stdout
    assert "[OK]" in result.stdout and "Итого:" in result.stdout
