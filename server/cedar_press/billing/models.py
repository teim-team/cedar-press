"""Billing plan types and configured annual price records."""

from dataclasses import dataclass
from typing import Literal

Tier = Literal["press", "press_pro"]
Cohort = Literal["early_access", "standard"]


@dataclass(frozen=True)
class Price:
    id: str
    tier: str
    cohort: str
    amount: int
