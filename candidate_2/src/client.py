from .logger import setup_logger
import os
import time
import requests
from dotenv import load_dotenv
from pathlib import Path
from typing import Any
from .exceptions import GitHubApiError, ResourceNotFound


load_dotenv()

logger = setup_logger(__name__)
TIMEOUT = (5, 30)


class GitHubClient:
    BASE_URL = "https://api.github.com"
    
    def __init__(
        self,
        token: str | None = None,
        max_retries: int = 5,
        base_delay: float = 1,
        max_backoff: float = 60,
        max_rate_limit_wait: float = 60,
        raw_dir: str = "data/raw"    
    ) -> None:
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_backoff = max_backoff
        self.max_rate_limit_wait = max_rate_limit_wait
        self.raw_dir = Path(raw_dir)
        
        # Instantiating a Session
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/vnd.github+json",
                "X-Github-Api-Version": "2022-11-28",
                "User-Agent": "github-data-ingestion-pipeline/1.0"
            }
        )
        
        token = token or os.getenv("GITHUB_TOKEN")
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
            
        else:
            logger.warning(
                "GITHUB_TOKEN not set - running unauthenticated..."
            )
            
        #Methods to implement
        
        # REPO RELATED
        # get_rate_limit()
        # get_repo()
        # fetch_org_repos()
        
    # Internal helpers
    def _backoff(self, attempt: int, reason: str) -> None:
        """Implementation of backoff"""
        if attempt == self.max_retries:
            logger.error(f"{reason} - giving up after {self.max_retries} attempts")
            return
        
        delay = min(self.max_backoff, self.base_delay * 2 ** (attempt - 1))
        logger.warning(
            f"{reason} - retrying in {delay} (attempt {attempt} / {self.max_retries})"
        )
        time.sleep(delay)
        
    def _handle_rate_limit(self, response: requests.Response) -> None:
        """Wait for the reset if it is within max_rate_limit_wait, else fail fast"""
        retry_after = response.headers.get("Retry-After")
        reset_header = response.headers.get("X-RateLimit-Reset")
        
        if retry_after:
            wait_seconds = float(retry_after)
        elif reset_header:
            wait_seconds = max(0, int(reset_header) - time.time()) + 1
        else:
            wait_seconds = self.max_rate_limit_wait
            
        if wait_seconds > self.max_rate_limit_wait:
            logger.error(
                f"Rate limit resets in {wait_seconds:.0f}s, over the {self.max_rate_limit_wait} max - failing fast"
            )
            raise GitHubApiError(
                f"Rate limit exhausted; resets in {wait_seconds:.0f}s "
                f"(Max wait is {self.max_rate_limit_wait}s)"
            )
            
        logger.warning(
            f"Rate limit hit. Waiting {wait_seconds:.0f}s"
        )
        time.sleep(wait_seconds)    
    
    
    def _request(
        self, method: str, url: str, params: dict | None = None
    ) -> requests.Response:
        """Makes a request with timeouts, retry/backoffs and rate-limit handling"""
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    params = params,
                    timeout= TIMEOUT
                )
            except (requests.Timeout, requests.ConnectionError) as exc:
                self._backoff(attempt, f"Network error ({type(exc).__name__})")
                continue
            
            status = response.status_code
            
            if 200 <= status < 300:
                return response
            
            if status == 404:
                logger.error(f"Resource not found: {url}")
                raise ResourceNotFound(f"Resource not found: {url}")
            
            if status == 429 or (
                status == 403 and response.headers.get("X-RateLimit-Remaining") == "0"
            ):
                self._handle_rate_limit(response)
                continue
            
            if status >= 500:
                self._backoff(attempt, f"Server error {status}")
                continue
            
            logger.error(f"Request to {url} failed: {status} {response.text[:200]}")
            raise GitHubApiError(f"Github returned {status} for {url}")
        
        raise GitHubApiError(f"Gave up on {url} after {self.max_retries} attempts")
    

    @staticmethod
    def _parse_json(response: requests.Response, expected_type: type) -> Any :
        """Parse JSON and check its top-level type (list or dict)"""
        try:
            data = response.json()
        except ValueError as exc:
            logger.error(f"Malformed JSON {response.url}: {exc}")
            raise GitHubApiError(f"Malformed JSON from {response.url}") from exc
        
        if not isinstance(data, expected_type):
            logger.error(
                f"Expected {expected_type.__name__} from {response.url}, got {type(data).__name__}"
            )
            raise GitHubApiError(f"Unexpected response shape from {response.url}")
        
        return data
        
    
    # Public helpers
    
    def get_rate_limit(self) -> dict:
        """
        Returns the 'core' quota: {'limit', 'used', 'remaining', 'reset'}
        """
        response = self._request("GET", f"{self.BASE_URL}/rate_limit")
        data = self._parse_json(response, dict)
        try:
            return data["resources"]["core"]
        except (KeyError, TypeError) as exc:
            logger.error("/rate_limit response has no resources.core section")
            raise GitHubApiError("Unexpected /rate_limit response shape") from exc
        
        
    def get_repo(self, owner: str, repo: str) -> dict:
        """
        Fetch a single repo 
        """
        response = self._request("GET", f"{self.BASE_URL}/repos/{owner}/{repo}")
        return self._parse_json(response, dict)
    
    
    def fetch_org_repos(self, org: str, run_timestamp:str) -> list[dict]:
        """
        Fetch every page of an orgs repos, saving each raw page first.
        """
        org_dir = self.raw_dir / org
        org_dir.mkdir(parents=True, exist_ok=True)
        
        repos: list[dict] = []
        url = f"{self.BASE_URL}/orgs/{org}/repos"
        params: dict | None = {"per_page": 100}
        
        page_number = 1
        
        while url:
            response = self._request("GET", url, params=params)
            
            #Saving the untouched response body before parsing anything
            raw_path = org_dir / f"{run_timestamp}_page{page_number}.json"
            raw_path.write_bytes(response.content)
            
            #Parsing it
            repos.extend(self._parse_json(response, list))
            
            #Getting the next page if there is one
            url = response.links.get("next", {}).get("url")
            params = None
            page_number += 1
            
        logger.info(
            f"Fetched {len(repos)} repos for {org} in {page_number - 1} page(s)"
        )
        return repos