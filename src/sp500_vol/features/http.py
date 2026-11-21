import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

RETRY = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[429, 500, 502, 503, 504],
    respect_retry_after_header=True,
    retry_after_max=60,
    # last answer is returned, so the clients show the status and not the URL with the key
    raise_on_status=False,
)

# urllib3 logs the URL on each retry, the FRED URL contains the API key
logging.getLogger("urllib3").setLevel(logging.ERROR)


def get_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=RETRY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session
