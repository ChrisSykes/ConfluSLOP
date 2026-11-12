"""Collect all space keys (without personal spaces) and save them to spacekeys.txt."""
from confluence_common import SPACEKEYS_FILE, get_all, get_session


def get_space_keys(session):
    # type=global returns only normal spaces, personal spaces are left out
    spaces = get_all(session, "/rest/api/space", {"type": "global", "status": "current"})

    keys = []
    for space in spaces:
        key = space["key"]
        if key.startswith("~"):  # personal spaces start with ~, just in case
            continue
        keys.append(key)
    return sorted(keys)


if __name__ == "__main__":
    keys = get_space_keys(get_session())

    with open(SPACEKEYS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(keys))

    print(f"Saved {len(keys)} space keys to {SPACEKEYS_FILE}")
