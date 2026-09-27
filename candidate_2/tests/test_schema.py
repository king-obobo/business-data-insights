from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.schema import Repo


def test_valid_record_passes(valid_repo_data):
    repo = Repo(**valid_repo_data)
    assert repo.id == 2471804
    assert repo.name == "stripe-node"
    assert isinstance(repo.created_at, datetime)


def test_missing_required_field_rejected(valid_repo_data):
    del valid_repo_data["name"]

    with pytest.raises(ValidationError) as exc_info:
        Repo(**valid_repo_data)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("name",) and e["type"] == "missing" for e in errors)


def test_wrong_type_rejected(valid_repo_data):
    valid_repo_data["stargazers_count"] = "not-a-number"

    with pytest.raises(ValidationError) as exc_info:
        Repo(**valid_repo_data)

    errors = exc_info.value.errors()
    assert any(e["loc"] == ("stargazers_count",) for e in errors)


def test_negative_count_rejected(valid_repo_data):
    valid_repo_data["stargazers_count"] = -5

    with pytest.raises(ValidationError) as exc_info:
        Repo(**valid_repo_data)

    errors = exc_info.value.errors()
    assert any("non-negative" in e["msg"] for e in errors)


def test_empty_name_rejected(valid_repo_data):
    valid_repo_data["name"] = ""

    with pytest.raises(ValidationError) as exc_info:
        Repo(**valid_repo_data)

    errors = exc_info.value.errors()
    assert any("must not be empty" in e["msg"] for e in errors)


def test_pushed_before_created_rejected(valid_repo_data):
    valid_repo_data["pushed_at"] = "2011-01-01T00:00:00Z"  # before created_at

    with pytest.raises(ValidationError) as exc_info:
        Repo(**valid_repo_data)

    assert "pushed_at must not be before created_at" in str(exc_info.value)


def test_recently_pushed_archived_flag_set(valid_repo_data):
    valid_repo_data["archived"] = True
    valid_repo_data["pushed_at"] = datetime.now(timezone.utc).isoformat()

    repo = Repo(**valid_repo_data)

    assert repo.flagged_recently_pushed_archived is True


def test_archived_but_not_recently_pushed_flag_not_set(valid_repo_data):
    valid_repo_data["archived"] = True
    old_push = datetime.now(timezone.utc) - timedelta(days=365)
    valid_repo_data["pushed_at"] = old_push.isoformat()
    valid_repo_data["created_at"] = "2011-09-28T00:28:33Z"

    repo = Repo(**valid_repo_data)

    assert repo.flagged_recently_pushed_archived is False