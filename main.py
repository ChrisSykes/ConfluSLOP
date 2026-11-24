import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    "check-spacekeys.py",
    "check-groups.py",
    "check-activity.py",
    "create-page-raport.py",
]

SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(name):
    print(f"\n=== Running {name} ===")
    result = subprocess.run([sys.executable, name], cwd=SCRIPT_DIR, check=False)
    return result.returncode == 0


if __name__ == "__main__":
    for name in SCRIPTS:
        if not run_script(name):
            print(f"\nFAILED: {name} - stopping, the remaining scripts were not run.")
            sys.exit(1)
        print(f"OK: {name}")

    print("\nAll scripts finished successfully.")
