import json
import logging
import time

import pytest
import requests
import responses

from src.client import TIMEOUT, GitHubClient
from src.exceptions import GitHubApiError, ResourceNotFound

API = "https://api.github.com"
REPO_URL = f"{API}/repos/acme/widget"
ORG_URL = f"{API}/orgs/acme/repos"
RUN_TS = "20260921T120000Z"


# ---------- helpers (the `client` and `sleeps` fixtures live in conftest.py) ----------


def repo_page(*ids):
    """A JSON page body containing minimal fake repos."""
    return json.dumps([{"id": i, "name": f"repo{i}"} for i in ids])


def add_json(url, body, **kwargs):
    responses.add(
        responses.GET, url, body=body, content_type="application/json", **kwargs
    )


# ---------- required scenario 1: pagination ----------


@responses.activate
def test_pagination_follows_link_header_across_three_pages(client, tmp_path):
    """Proves: pages are followed via Link rel="next" until it disappears,
    and each raw page is saved byte-for-byte."""
    page2_url = f"{API}/organizations/1/repos?page=2"
    page3_url = f"{API}/organizations/1/repos?page=3"
    page1, page2, page3 = repo_page(1, 2), repo_page(3, 4), repo_page(5, 6)

    add_json(ORG_URL, page1, headers={"Link": f'<{page2_url}>; rel="next"'})
    add_json(
        page2_url,
        page2,
        headers={"Link": f'<{page3_url}>; rel="next", <{page3_url}>; rel="last"'},
    )
    add_json(page3_url, page3)  # no Link header -> last page

    repos = client.fetch_org_repos("acme", RUN_TS)

    assert [r["id"] for r in repos] == [1, 2, 3, 4, 5, 6]
    assert len(responses.calls) == 3
    assert "per_page=100" in responses.calls[0].request.url # type: ignore

    raw_dir = tmp_path / "acme"
    assert sorted(p.name for p in raw_dir.iterdir()) == [
        f"{RUN_TS}_page1.json",
        f"{RUN_TS}_page2.json",
        f"{RUN_TS}_page3.json",
    ]
    assert (raw_dir / f"{RUN_TS}_page1.json").read_bytes() == page1.encode()


# ---------- required scenario 2: timeout / connection error then retry ----------


@pytest.mark.parametrize(
    "error", [requests.Timeout("timed out"), requests.ConnectionError("dropped")]
)
@responses.activate
def test_network_error_is_retried_then_succeeds(client, sleeps, error):
    """Proves: a transient network failure is retried and the call recovers."""
    responses.add(responses.GET, REPO_URL, body=error)
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    result = client.get_repo("acme", "widget")

    assert result["name"] == "widget"
    assert len(responses.calls) == 2
    assert sleeps == [1]


@responses.activate
def test_network_errors_give_up_after_max_retries(client, sleeps):
    """Proves: persistent network failure ends in a clean GitHubApiError."""
    responses.add(responses.GET, REPO_URL, body=requests.Timeout("timed out"))

    with pytest.raises(GitHubApiError, match="Gave up"):
        client.get_repo("acme", "widget")

    assert len(responses.calls) == 3  # max_retries
    assert sleeps == [1, 2]  # no pointless sleep after the final attempt


# ---------- required scenario 3: 5xx backoff ----------

@responses.activate
def test_5xx_backs_off_exponentially_then_succeeds(client, sleeps):
    """Proves: delays double (1s, 2s) and the call succeeds once GitHub recovers."""
    responses.add(responses.GET, REPO_URL, status=500)
    responses.add(responses.GET, REPO_URL, status=502)
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    result = client.get_repo("acme", "widget")

    assert result["id"] == 1
    assert len(responses.calls) == 3
    assert sleeps == [1, 2]


@responses.activate
def test_5xx_fails_cleanly_after_max_retries(client, sleeps):
    """Proves: a permanently failing server gives a GitHubApiError, not a hang."""
    responses.add(responses.GET, REPO_URL, status=503)

    with pytest.raises(GitHubApiError, match="Gave up"):
        client.get_repo("acme", "widget")

    assert len(responses.calls) == 3
    assert sleeps == [1, 2]


# ---------- required scenario 4: rate limiting ----------


@pytest.mark.parametrize("status", [403, 429])
@responses.activate
def test_rate_limit_within_cap_waits_then_retries(client, sleeps, status):
    """Proves: if the reset is close (<= max wait), the client waits and retries."""
    reset = int(time.time()) + 5
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)}
    responses.add(responses.GET, REPO_URL, status=status, headers=headers)
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    result = client.get_repo("acme", "widget")

    assert result["name"] == "widget"
    assert len(sleeps) == 1
    assert 0 < sleeps[0] <= 7  # about 5s until reset, plus the 1s safety margin


@responses.activate
def test_rate_limit_beyond_cap_fails_fast(client, sleeps):
    """Proves: if the reset is far away, the client fails fast and never sleeps."""
    reset = int(time.time()) + 3600
    headers = {"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": str(reset)}
    responses.add(responses.GET, REPO_URL, status=429, headers=headers)

    with pytest.raises(GitHubApiError, match="Rate limit exhausted"):
        client.get_repo("acme", "widget")

    assert sleeps == []
    assert len(responses.calls) == 1  # did not keep hammering GitHub


@responses.activate
def test_retry_after_header_is_used_when_present(client, sleeps):
    """Proves: Retry-After takes priority over X-RateLimit-Reset."""
    responses.add(responses.GET, REPO_URL, status=429, headers={"Retry-After": "2"})
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    client.get_repo("acme", "widget")

    assert sleeps == [2.0]


@responses.activate
def test_rate_limit_without_headers_waits_the_maximum(client, sleeps):
    """Proves: with no timing headers at all, the client uses max_rate_limit_wait."""
    responses.add(responses.GET, REPO_URL, status=429)
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    client.get_repo("acme", "widget")

    assert sleeps == [60]


# ---------- required scenario 5: malformed JSON ----------


@responses.activate
def test_malformed_json_is_logged_and_wrapped(client, tmp_path, caplog):
    """Proves: a truncated body is logged and surfaces as GitHubApiError (not a raw
    JSONDecodeError), and the raw page was already saved before parsing failed."""
    truncated = '[{"id": 1, "name": "repo1"}, {"id": 2, "na'
    add_json(ORG_URL, truncated)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(GitHubApiError, match="Malformed JSON") as exc_info:
            client.fetch_org_repos("acme", RUN_TS)

    assert "Malformed JSON" in caplog.text
    assert isinstance(exc_info.value.__cause__, ValueError)
    saved = tmp_path / "acme" / f"{RUN_TS}_page1.json"
    assert saved.read_bytes() == truncated.encode()


# ---------- extras (not listed in the assessment; they cover remaining branches) ----------


@responses.activate
def test_404_raises_resource_not_found(client, sleeps):
    responses.add(responses.GET, REPO_URL, status=404)

    with pytest.raises(ResourceNotFound):
        client.get_repo("acme", "widget")

    assert len(responses.calls) == 1  # 404 is not retried


@pytest.mark.parametrize(
    "status, headers",
    [(401, {}), (422, {}), (403, {"X-RateLimit-Remaining": "100"})],
)
@responses.activate
def test_other_4xx_fail_immediately_without_retry(client, sleeps, status, headers):
    responses.add(responses.GET, REPO_URL, status=status, headers=headers)

    with pytest.raises(GitHubApiError, match=f"returned {status}"):
        client.get_repo("acme", "widget")

    assert len(responses.calls) == 1
    assert sleeps == []


@responses.activate
def test_unexpected_json_shape_is_rejected(client):
    add_json(REPO_URL, json.dumps([1, 2, 3]))  # a repo should be a dict, not a list

    with pytest.raises(GitHubApiError, match="Unexpected response shape"):
        client.get_repo("acme", "widget")


@responses.activate
def test_get_rate_limit_returns_core_quota(client):
    core = {"limit": 5000, "used": 1, "remaining": 4999, "reset": 1}
    responses.add(
        responses.GET, f"{API}/rate_limit", json={"resources": {"core": core}}
    )

    assert client.get_rate_limit() == core


@responses.activate
def test_get_rate_limit_without_core_section_raises(client):
    responses.add(responses.GET, f"{API}/rate_limit", json={"resources": {}})

    with pytest.raises(GitHubApiError, match="Unexpected /rate_limit"):
        client.get_rate_limit()


@responses.activate
def test_every_request_sets_an_explicit_timeout(client):
    responses.add(responses.GET, REPO_URL, json={"id": 1, "name": "widget"})

    client.get_repo("acme", "widget")

    assert responses.calls[0].request.req_kwargs["timeout"] == TIMEOUT # type: ignore


def test_token_is_sent_as_bearer_and_api_version_is_pinned(client):
    assert client.session.headers["Authorization"] == "Bearer test-token"
    assert client.session.headers["X-GitHub-Api-Version"] == "2022-11-28"


def test_missing_token_warns_and_runs_unauthenticated(
    monkeypatch, tmp_path, sleeps, caplog
):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    with caplog.at_level(logging.WARNING):
        unauth_client = GitHubClient(raw_dir=str(tmp_path))

    assert "GITHUB_TOKEN not set" in caplog.text
    assert "Authorization" not in unauth_client.session.headers