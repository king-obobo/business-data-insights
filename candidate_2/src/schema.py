from datetime import datetime, timezone
from pydantic import BaseModel, field_validator, model_validator


class Repo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    html_url: str
    description: str | None = None
    stargazers_count: int
    forks_count: int
    open_issues_count: int
    archived: bool
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    flagged_recently_pushed_archived: bool = False

    # Working on the field validators first
    @field_validator("name", "full_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("stargazers_count", "forks_count", "open_issues_count")
    @classmethod
    def validate_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("must be non-negative")
        return value


    # Model validators next
    @model_validator(mode="after")
    def validate_pushed_after_created(self) -> "Repo":
        if self.pushed_at < self.created_at:
            raise ValueError("pushed_at must not be before created_at")
        return self

    @model_validator(mode="after")
    def flag_recently_pushed_archived(self) -> "Repo":
        if self.archived:
            days_since_push = (datetime.now(timezone.utc) - self.pushed_at).days
            if days_since_push < 30:
                self.flagged_recently_pushed_archived = True
        return self