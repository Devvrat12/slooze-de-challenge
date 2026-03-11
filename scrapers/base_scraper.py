import time
import random
import logging
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Edge/122.0.0.0 Safari/537.36",
]


class BaseScraper:
    def __init__(
        self,
        source_name: str,
        min_delay: float = 2.0,
        max_delay: float = 6.0,
        max_retries: int = 3,
    ):
        self.source_name = source_name
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.session = requests.Session()
        self.logger = logging.getLogger(source_name)

    def _get_headers(self) -> dict:

        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "keep-alive",
            "DNT": "1",
        }

    def _polite_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.debug(f"Sleeping {delay:.1f}s before next request...")
        time.sleep(delay)

    def fetch(self, url: str, params: dict = None):

        for attempt in range(1, self.max_retries + 1):
            try:
                self._polite_delay()
                response = self.session.get(
                    url,
                    headers=self._get_headers(),
                    params=params,
                    timeout=15,
                )
                response.raise_for_status()
                self.logger.info(f"[{attempt}] SUCCESS: {url}")
                return BeautifulSoup(response.text, "lxml")

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response else "?"
                self.logger.warning(f"[{attempt}] HTTP {status} for {url}")
                if status == 429:
                    time.sleep(2 ** attempt * 5)  # back off hard on rate limit
                elif status in (403, 404):
                    return None

            except requests.exceptions.ConnectionError:
                self.logger.warning(f"[{attempt}] Connection error")
                time.sleep(2 ** attempt)

            except requests.exceptions.Timeout:
                self.logger.warning(f"[{attempt}] Timeout")
                time.sleep(2 ** attempt)

        self.logger.error(f"All {self.max_retries} attempts failed for {url}")
        return None

    def scrape(self) -> list:
        raise NotImplementedError("Subclasses must implement scrape()")
