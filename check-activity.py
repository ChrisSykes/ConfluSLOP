"""Check total views for each space using the Viewtracker report endpoint.

    /report/spaces/{spaceKey}/visitors

The endpoint returns one row per user with "views". Total views of a space = sum of all rows.

Results are saved to activity.json.
"""
import json

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "activity.json"

# ask for up to 30000 rows per call (the endpoint default is only 10)
LIMIT = 30000

# Put here whatever comes in the browser URL BEFORE "/report/spaces/..."
# (for example "/rest/viewtracker/1.0"). Leave "" if the path starts directly with /report.
VIEWTRACKER_BASE = "/rest/viewtracker/1.0"


def get_visitor_rows(session, space_key):
    """Load all rows of the visitors report, page by page."""
    url = f"{CONFLUENCE_URL}{VIEWTRACKER_BASE}/report/spaces/{space_key}/visitors"
    rows = []
    start = 0

    while True:
        response = session.get(url, params={"start": start, "limit": LIMIT}, timeout=120)
        response.raise_for_status()
        data = response.json()

        if not data.get("success", True):
            raise RuntimeError(f"Viewtracker error for {space_key}: {data.get('error')}")

        results = data.get("results", [])
        rows.extend(results)

        start += len(results)
        if not results or start >= data.get("total", 0):
            break

    return rows


def get_total_views(session, space_key):
    # CHANGED: only total views, contributors and the 90 day filter were removed
    return sum(row["views"] for row in get_visitor_rows(session, space_key))


if __name__ == "__main__":
    session = get_session()
    results = {}

    for space_key in load_spacekeys():
        views = get_total_views(session, space_key)
        results[space_key] = {"views": views}
        print(f"{space_key}: {views} views")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")
