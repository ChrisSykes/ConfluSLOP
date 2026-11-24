"""Create (or update) a Confluence page with one table row per space key.

Reads: spacekeys.txt, groups.json, activity.json (run the check scripts first).
"""
import argparse
import json
from datetime import date
from html import escape

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

REPORT_SPACE = "TKR"                      # space where the report page will live
REPORT_TITLE = "Confluence security report"
PREVIEW_FILE = "report-preview.html"
SCRIPT_VERSION = "v6 (current groups / suggested groups / total views)"  # ADDED: shown in console and on the page


def load_json(filename):
    try:
        with open(filename, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: {filename} not found, columns will be empty")
        return {}


def build_table(space_keys, groups, activity):
    # CHANGED: new columns, same names as you asked for
    header = ["Space key", "Status", "Current groups in space", "Suggested groups", "Total views"]
    rows = ["<tr>" + "".join(f"<th>{h}</th>" for h in header) + "</tr>"]

    for key in space_keys:
        g = groups.get(key, {})
        a = activity.get(key, {})

        # every cell is escaped, the groups are put one under another
        cells = [
            escape(key),
            escape(g.get("status", "n/a")),
            "<br/>".join(escape(name) for name in g.get("current_groups", [])),
            "<br/>".join(escape(name) for name in g.get("suggested_groups", [])),
            escape(str(a.get("views", "n/a"))),
        ]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

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
    # ADDED: --dry-run builds the report but does not touch Confluence
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="do not create/update the page, save a preview file instead")
    args = parser.parse_args()

    table = build_table(load_spacekeys(), load_json("groups.json"), load_json("activity.json"))
    body = f"<p>Generated: {date.today().isoformat()} - script {SCRIPT_VERSION}</p>{table}"
    print(f"Running create-page-raport.py {SCRIPT_VERSION}")

    if args.dry_run:
        # ADDED: save the page content locally so you can check it
        with open(PREVIEW_FILE, "w", encoding="utf-8") as f:
            f.write(body)
        print(f"Dry run: page was NOT created. Preview saved to {PREVIEW_FILE}")
    else:
        url = save_page(get_session(), REPORT_TITLE, body)
        print(f"Report page: {url}")
