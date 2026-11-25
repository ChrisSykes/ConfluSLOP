"""Small helpers shared by all check scripts."""
import os
import sys
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set these as environment variables, or edit the defaults here.
CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://confluence.example.com").rstrip("/")
CONFLUENCE_TOKEN = os.environ.get("CONFLUENCE_TOKEN", "")  # Personal Access Token

SPACEKEYS_FILE = "spacekeys.txt"

# ADDED: Confluence answers "429 Too Many Requests" when we call it too fast.
DELAY_BETWEEN_REQUESTS = 0.3   # seconds to wait before every request, raise it if 429 still happens
MAX_RETRIES = 6                # how many times a failed GET (429/502/503/504) is tried again


# ADDED: a session that waits a little before every request
class ThrottledSession(requests.Session):
    def request(self, *args, **kwargs):
        time.sleep(DELAY_BETWEEN_REQUESTS)
        return super().request(*args, **kwargs)


def get_session():
    session = ThrottledSession()  # CHANGED: was requests.Session()
    session.headers["Authorization"] = f"Bearer {CONFLUENCE_TOKEN}"
    session.headers["Accept"] = "application/json"
    # session.verify = "/path/to/company-ca.pem"   # uncomment if you use an internal CA

    # ADDED: if Confluence says 429 (or a temporary 5xx), wait and try the same GET again.
    # The waiting time grows with every try and follows the "Retry-After" header if there is one.
    retry = Retry(total=MAX_RETRIES, backoff_factor=2, status_forcelist=[429, 502, 503, 504],
                  allowed_methods=["GET"], raise_on_status=False)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
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

        # Confluence adds a "next" link only when there is another page
        if not results or "next" not in data.get("_links", {}):
            break
        start += len(results)

    return all_results


def load_spacekeys():
    """Read the space keys produced by check-spacekeys.py."""
    if not os.path.exists(SPACEKEYS_FILE):
        sys.exit(f"{SPACEKEYS_FILE} not found - run check-spacekeys.py first.")
    with open(SPACEKEYS_FILE, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
