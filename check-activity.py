import json
from datetime import date, timedelta
from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "activity.json"
DAYS = 90

VIEWTRACKER_PATH = "/rest/viewtracker/1.0/space/{space_key}/stats?from={from_date}&to={to_date}"

VIEWS_FIELD = "views"
EDITS_FIELD = "edits"

def get_activity(session, space_key):
    today = date.today()
    path = VIEWTRACKER_PATH.format(
        space_key=space_key,
        from_date=(today - timedelta(days=DAYS)).isoformat(),
        to_date=today.isoformat(),
    )
    response = session.get(CONFLUENCE_URL + path, timeout=30)
    response.raise_for_status()
    data = response.json()

    return {
        "views": data.get(VIEWS_FIELD, 0),
        "edits": data.get(EDITS_FIELD, 0),
    }

if __name__ == "__main__":
    session = get_session()
    results = {}

    for space_key in load_spacekeys():
        activity = get_activity(session, space_key)
        results[space_key] = activity
        print(f"{space_key}: {activity['views']} views, {activity['edits']} edits")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")
