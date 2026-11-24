"""Run the checks and create the report page.

    python main.py             use existing data files, create only the missing ones
    python main.py --fetch     fetch new data: run all checks again
    python main.py --dry-run   do everything except creating/updating the Confluence page
                               (a preview is saved to report-preview.html instead)

Options can be combined:  python main.py --fetch --dry-run

If any script fails we stop, so the report is never built from partial data.
"""
import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ADDED: each check script and the file it creates
CHECKS = [
    ("check-spacekeys.py", "spacekeys.txt"),
    ("check-groups.py", "groups.json"),
    ("check-activity.py", "activity.json"),
]
REPORT_SCRIPT = "create-page-raport.py"

# Run from the folder where the scripts live, so the .txt/.json files are found
SCRIPT_DIR = Path(__file__).resolve().parent


def run_script(name, extra_args=()):
    print(f"\n=== Running {name} ===")
    result = subprocess.run([sys.executable, name, *extra_args], cwd=SCRIPT_DIR)
    return result.returncode == 0


def fail(name):
    print(f"\nFAILED: {name} - stopping, the remaining scripts were not run.")
    sys.exit(1)


if __name__ == "__main__":
    # ADDED: command line options
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--fetch", action="store_true",
                        help="fetch new data, run all checks even if the files exist")
    parser.add_argument("--dry-run", action="store_true",
                        help="do not create/update the Confluence page")
    args = parser.parse_args()

    for script, output_file in CHECKS:
        # ADDED: skip the check when its file already exists (unless --fetch)
        if not args.fetch and (SCRIPT_DIR / output_file).exists():
            # ADDED: show when the file was created, so old data is easy to spot
            created = datetime.fromtimestamp((SCRIPT_DIR / output_file).stat().st_mtime)
            print(f"\nSKIPPED: {script} - using existing {output_file} (created {created:%Y-%m-%d %H:%M})")
            continue

        if not run_script(script):
            fail(script)
        print(f"OK: {script}")

    report_args = ["--dry-run"] if args.dry_run else []
    if not run_script(REPORT_SCRIPT, report_args):
        fail(REPORT_SCRIPT)
    print(f"OK: {REPORT_SCRIPT}")

    print("\nAll done.")
