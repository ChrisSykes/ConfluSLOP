"""Create (or update) a Confluence page with one table row per space key.

Reads: spacekeys.txt, groups.json, activity.json (run the check scripts first).
"""
import json
from datetime import date
from html import escape

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

REPORT_SPACE = "SEC"                      # space where the report page will live
REPORT_TITLE = "Confluence security report"


def load_json(filename):
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found, columns will be empty")
        return {}


def build_table(space_keys, groups, activity):
    header = ["Space key", "Status", "Wrong groups", "Missing groups",
              "Views (90d)", "Edits (90d)"]
    rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"]

    for key in space_keys:
        g = groups.get(key, {})
        a = activity.get(key, {})
        cells = [
            key,
            g.get("status", "n/a"),
            ", ".join(g.get("groups_wrong", [])),
            ", ".join(g.get("groups_missing", [])),
            a.get("views", "n/a"),
            a.get("edits", "n/a"),
        ]
        rows.append("<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in cells) + "</tr>")

    return "<table><tbody>" + "".join(rows) + "</tbody></table>"


def find_page(session, title):
    """Return the existing report page (id + version) or None."""
    response = session.get(
        f"{CONFLUENCE_URL}/rest/api/content",
        params={"spaceKey": REPORT_SPACE, "title": title, "expand": "version"},
        timeout=30,
    )
    response.raise_for_status()
    results = response.json()["results"]
    return results[0] if results else None


def save_page(session, title, body):
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": REPORT_SPACE},
        "body": {"storage": {"value": body, "representation": "storage"}},
    }

    existing = find_page(session, title)
    if existing:
        payload["version"] = {"number": existing["version"]["number"] + 1}
        response = session.put(
            f"{CONFLUENCE_URL}/rest/api/content/{existing['id']}", json=payload, timeout=30)
    else:
        response = session.post(f"{CONFLUENCE_URL}/rest/api/content", json=payload, timeout=30)

    response.raise_for_status()
    page = response.json()
    return CONFLUENCE_URL + page["_links"]["webui"]


if __name__ == "__main__":
    session = get_session()

    table = build_table(load_spacekeys(), load_json("groups.json"), load_json("activity.json"))
    body = f"<p>Generated: {date.today().isoformat()}</p>{table}"

    url = save_page(session, REPORT_TITLE, body)
    print(f"Report page: {url}")
