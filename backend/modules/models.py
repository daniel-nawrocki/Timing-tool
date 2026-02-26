from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HoleRecord:
    """A single blast hole loaded from CSV."""

    id: str
    x: float
    y: float
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class RowDefinition:
    """User-assigned row with ordered hole ids.

    start_from_prev_hole indicates which hole number in the previous row aligns with
    the first hole in this row for row-to-row timing.
    """

    row_id: int
    hole_ids: list[str]
    start_from_prev_hole: int = 1


@dataclass
class TimingConstraints:
    hole_to_hole_min: int
    hole_to_hole_max: int
    row_to_row_min: int
    row_to_row_max: int


@dataclass
class BlastData:
    holes: list[dict[str, Any]]
    rows: list[dict[str, Any]]
    constraints: dict[str, Any] = field(default_factory=dict)
    offsets: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        """Maintain compatibility with older payloads that used `offsets`."""
        if (not self.constraints) and self.offsets:
            self.constraints = dict(self.offsets)