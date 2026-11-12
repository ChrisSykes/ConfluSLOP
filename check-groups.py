
import json

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "groups.json"


class GroupNameChecker:
    """Knows the naming convention and compares it with the groups found in a space."""

    SUFFIXES = ["VIEW", "EDIT", "Admin"]

    def expected_groups(self, space_key):
        return [f"sec-confluence-{space_key}-{suffix}" for suffix in self.SUFFIXES]

    def check(self, space_key, found_groups):
        expected = {name.lower(): name for name in self.expected_groups(space_key)}
        found = {name.lower(): name for name in found_groups}

        wrong = [found[name] for name in found if name not in expected]
        missing = [expected[name] for name in expected if name not in found]

        return {
            "groups_found": sorted(found.values()),
            "groups_wrong": sorted(wrong),
            "groups_missing": sorted(missing),
            "status": "OK" if not wrong and not missing else "FAIL",
        }


def get_space_subjects(session, space_key):
    """Return (group names, user names) that have any permission in the space."""


    url = f"{CONFLUENCE_URL}/rest/api/space/{space_key}/permissions"
    response = session.get(url, timeout=30)
    response.raise_for_status()
    data = response.json()

    permissions = data.get("results", []) if isinstance(data, dict) else data

    groups = set()
    users = set()
    for permission in permissions:
        subject = permission.get("subject", {})
        if subject.get("type") == "group":
            groups.add(subject["name"])
        elif subject.get("type") == "user":
            users.add(subject.get("name") or subject.get("displayName") or "unknown user")
    return groups, users


if __name__ == "__main__":
    session = get_session()
    checker = GroupNameChecker()
    results = {}

    for space_key in load_spacekeys():
        groups, users = get_space_subjects(session, space_key)
        result = checker.check(space_key, groups)

        for user in sorted(users):
            result["groups_wrong"].append(f"user: {user}")
            result["status"] = "FAIL"

        results[space_key] = result
        print(f"{space_key}: {result['status']}")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")