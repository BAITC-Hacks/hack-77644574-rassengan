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
