import json
from datetime import datetime, timedelta, timezone

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "activity.json"
DAYS = 90

# Put here whatever comes in the browser URL BEFORE "/report/spaces/..."
# (for example "/rest/viewtracker/1.0"). Leave "" if the path starts directly with /report.
VIEWTRACKER_BASE = ""


def get_report_rows(session, space_key, report):
    """Load all rows of a report ('visitors' or 'contributors'), page by page."""
    url = f"{CONFLUENCE_URL}{VIEWTRACKER_BASE}/report/spaces/{space_key}/{report}"
    rows = []
    start = 0

    while True:
        response = session.get(url, params={"start": start, "limit": 100}, timeout=30)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", True):
            raise RuntimeError(f"Viewtracker error for {space_key}/{report}: {data.get('error')}")

        results = data.get("results", [])
        rows.extend(results)

        start += len(results)
        if not results or start >= data.get("total", 0):
            break

    return rows


def keep_recent(rows):
    """Keep only rows where the user's last view is within the last DAYS days."""
    limit_date = datetime.now(timezone.utc) - timedelta(days=DAYS)
    recent = []
    for row in rows:
        # e.g. "2026-11-12T15:25:04.567+01:00"
        last_view = datetime.fromisoformat(row["lastViewDateFormatted"])
        if last_view >= limit_date:
            recent.append(row)
    return recent


def get_activity(session, space_key):
    visitors = keep_recent(get_report_rows(session, space_key, "visitors"))
    contributors = keep_recent(get_report_rows(session, space_key, "contributors"))

    return {
        "visitors": len(visitors),                          # users who viewed in last 90 days
        "views": sum(row["views"] for row in visitors),     # their total views (not only the last 90 days)
        "contributors": len(contributors),                  # contributors active in last 90 days
    }


if __name__ == "__main__":
    session = get_session()
    results = {}

    for space_key in load_spacekeys():
        activity = get_activity(session, space_key)
        results[space_key] = activity
        print(f"{space_key}: {activity['visitors']} visitors, "
              f"{activity['views']} views, {activity['contributors']} contributors")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")
