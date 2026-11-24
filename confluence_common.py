import os
import sys

import requests


CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://confluence.example.com").rstrip("/")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")  # Personal Access Token

SPACEKEYS_FILE = "spacekeys.txt"


def get_session():
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {CONFLUENCE_TOKEN}"
    session.headers["Accept"] = "application/json"
    return session


def get_all(session, path, params=None, page_size=100):
    """GET a paginated Confluence endpoint and return all 'results' as one list."""
    params = dict(params or {})
    params["limit"] = page_size
    start = 0
    all_results = []

    while True:
        params["start"] = start
        response = session.get(CONFLUENCE_URL + path, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])
        all_results.extend(results)

        if not results or "next" not in data.get("_links", {}):
            break
        start += len(results)
    return all_results


def load_spacekeys():
    if not os.path.exists(SPACEKEYS_FILE):
        sys.exit(f"{SPACEKEYS_FILE} not found - run check-spacekeys.py first.")
    with open(SPACEKEYS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
