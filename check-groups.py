import json

from confluence_common import CONFLUENCE_URL, get_session, load_spacekeys

RESULT_FILE = "groups.json"


class GroupNameChecker:


    SUFFIXES = ["VIEW", "EDIT", "Admin"]

    def expected_groups(self, space_key):
        return [f"sec-confluence-{space_key}-{suffix}" for suffix in self.SUFFIXES]


    def check(self, space_key, found_groups, found_users=()):


        expected = {name.lower(): name for name in self.expected_groups(space_key)}
        found = {name.lower(): name for name in found_groups}


        ad_groups = [found[name] for name in found if name in expected]

        wrong = [found[name] for name in found if name not in expected]
        wrong += [f"user: {user}" for user in found_users]

        missing = [expected[name] for name in expected if name not in found]

        if missing:
            status = "missing AD groups"
        elif wrong:
            status = "No"
        else:
            status = "Yes"

        return {
            "ad_groups": sorted(ad_groups),
            "groups_wrong": sorted(wrong),
            "groups_missing": sorted(missing),
            "status": status,
        }



def get_space_subjects(session, space_key):

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
        # CHANGED: users are passed to the checker, no extra loop needed
        result = checker.check(space_key, groups, users)

        results[space_key] = result
        print(f"{space_key}: {result['status']}")

    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Saved to {RESULT_FILE}")
