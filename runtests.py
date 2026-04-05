#!/usr/bin/env venv/bin/python3
import subprocess
import sys
import pytest

if __name__ == "__main__":
    lint = subprocess.run(
        ["venv/bin/ruff", "check", "app/", "tests/"],
        capture_output=True,
        text=True,
    )
    if lint.stdout:
        print(lint.stdout)
    if lint.returncode != 0:
        sys.exit(lint.returncode)

    sys.exit(pytest.main(["tests", "-v"]))
