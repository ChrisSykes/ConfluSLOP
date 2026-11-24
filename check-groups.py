"""Check which groups have permissions in each space and if they follow the naming convention.

Expected groups for space ABC (case does not matter):
    sec-confluence-ABC-VIEW
    sec-confluence-ABC-EDIT
    sec-confluence-ABC-Admin

Status:
    Custom groups naming  the space has groups that do not follow the naming convention
    missing groups        no custom groups, but one or more of the three groups are missing
    Yes                   all three groups are in the space and nothing else
    (if both apply, "Custom groups naming" wins)

Only groups are checked. Users added directly are ignored.
Results are saved to groups.json.

To see exactly what Confluence returns for one space (useful when results look wrong):
    python check-groups.py --raw 1001
"""
import argparse
import json

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "groups.json"

# CHANGED: groups that are allowed in every space besides the three AD groups.
# Example: ALLOWED_EXTRA_GROUPS = ["sec-confluence-users"]
ALLOWED_EXTRA_GROUPS = []

# CHANGED: the "Current groups in space" column shows ALL groups found in the space.
# To show only groups that start with some text, set it here, e.g. "sec-confluence-"
CURRENT_GROUPS_PREFIX = ""


class GroupNameChecker:
    """Knows the naming convention and compares it with the groups found in a space."""

    SUFFIXES = ["VIEW", "EDIT", "Admin"]

    def expected_groups(self, space_key):
        return [f"sec-confluence-{space_key}-{suffix}" for suffix in self.SUFFIXES]

    # CHANGED: new status logic, plus "suggested_groups" and a filtered "current_groups"
    def check(self, space_key, found_groups):
        # Names are compared in lowercase, so the check is NOT case sensitive
        expected = {name.lower(): name for name in self.expected_groups(space_key)}
        allowed = {name.lower() for name in ALLOWED_EXTRA_GROUPS}
        found = {name.lower() for name in found_groups}

        missing = [expected[name] for name in expected if name not in found]
        custom = found - set(expected) - allowed   # groups that do not follow the convention

        if custom:
            status = "Custom groups naming"
        elif missing:
            status = "missing groups"
        else:
            status = "Yes"

        # CHANGED: groups shown in the report column (all groups unless a prefix is set above)
        current = [name for name in found_groups
                   if name.lower().startswith(CURRENT_GROUPS_PREFIX.lower())]

        return {
            "status": status,
            "current_groups": sorted(current),
            "suggested_groups": sorted(missing),   # groups that should be added to the space
        }


def get_permissions(session, space_key):
    """Load all permission entries of a space (Confluence 9.1+ endpoint), page by page."""
    url = f"{CONFLUENCE_URL}/rest/api/space/{space_key}/permissions"
    limit = 1000
    start = 0
    all_entries = []

    while True:
        response = session.get(url, params={"start": start, "limit": limit}, timeout=60)
        response.raise_for_status()
        data = response.json()

        # the docs show a plain list, but also accept {"results": [...]}
        page = data.get("results", []) if isinstance(data, dict) else data

        # stop when there is nothing new (also when the server ignores start/limit
        # and sends the same list again)
        if not page or page == all_entries[:len(page)]:
            break
        all_entries.extend(page)
        start += len(page)

    return all_entries


def get_space_groups(session, space_key):
    """Return the names of all groups that have any permission in the space."""
    groups = set()

    for permission in get_permissions(session, space_key):
        # Each item looks like:
        # {"operation": {"targetType": "space", "operationKey": "read"},
        #  "subject": {"type": "group", "name": "confluence-users"}, "spaceKey": "PROJ"}
        subject = permission.get("subject", {})
        if subject.get("type") == "group":
            groups.add(subject["name"])
    return groups


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", metavar="SPACEKEY", help="print raw permissions of one space")
    args = parser.parse_args()

    session = get_session()

    if args.raw:
        print(json.dumps(get_permissions(session, args.raw), indent=2))
        raise SystemExit

    checker = GroupNameChecker()
    results = {}

    for space_key in load_spacekeys():
        groups = get_space_groups(session, space_key)
        result = checker.check(space_key, groups)

        results[space_key] = result
        # CHANGED: also print the groups that were found, so you can see why a status was set
        # CHANGED: print ALL groups found (also custom ones), so you can see why a status was set
        print(f"{space_key}: {result['status']}  | all groups found: {', '.join(sorted(groups)) or '-'}")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")
