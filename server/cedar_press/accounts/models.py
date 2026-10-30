"""Account and session domain records."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Subscriber:
    email: str
    tier: str | None
    account_id: str
    password_hash: str | None = None
    session_revision: str = ""


@dataclass(frozen=True)
class Session:
    email: str
    tier: str
    revision: str = field(default="", compare=False, repr=False)

    def as_payload(self) -> dict[str, object]:
        return {"email": self.email, "workspace_tier": self.tier}
