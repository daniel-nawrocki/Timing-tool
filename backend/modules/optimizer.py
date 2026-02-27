from __future__ import annotations

from collections import Counter
from math import floor
from typing import Any


class TimingOptimizer:
    """Optimize delays to minimize holes sharing the same delay."""

    def _parse_constraints(self, constraints: dict[str, Any]) -> dict[str, int]:
        required = [
            "hole_to_hole_min",
            "hole_to_hole_max",
            "row_to_row_min",
            "row_to_row_max",
        ]
        parsed: dict[str, int] = {}
        for key in required:
            if key not in constraints:
                raise ValueError(f"Missing constraint: {key}")
            parsed[key] = int(constraints[key])

        if parsed["hole_to_hole_min"] > parsed["hole_to_hole_max"]:
            raise ValueError("hole_to_hole_min must be <= hole_to_hole_max")
        if parsed["row_to_row_min"] > parsed["row_to_row_max"]:
            raise ValueError("row_to_row_min must be <= row_to_row_max")
        if parsed["hole_to_hole_min"] <= 0 or parsed["row_to_row_min"] <= 0:
            raise ValueError("Minimum delays must be positive integers")

        return parsed

    def _build_schedule(
        self, rows: list[dict[str, Any]], hole_delay: int, row_delay: int
    ) -> list[dict[str, Any]]:
        schedule: list[dict[str, Any]] = []
        row_starts: list[int] = []

        for row_idx, row in enumerate(rows):
            hole_ids = row.get("hole_ids", [])
            if not hole_ids:
                continue

            if row_idx == 0:
                start_time = 0
            else:
                prev_start = row_starts[row_idx - 1]
                start_from_prev_hole = int(row.get("start_from_prev_hole", 1))
                start_time = (
                    prev_start + ((start_from_prev_hole - 1) * hole_delay) + row_delay
                )

            row_starts.append(start_time)

            for pos, hole_id in enumerate(hole_ids, start=1):
                schedule.append(
                    {
                        "hole_id": str(hole_id),
                        "row_id": row.get("row_id", row_idx + 1),
                        "position_in_row": pos,
                        "delay_ms": start_time + ((pos - 1) * hole_delay),
                        "row_reference_hole": int(row.get("start_from_prev_hole", 1)),
                        "hole_to_hole_ms": hole_delay,
                        "row_to_row_ms": row_delay,
                    }
                )

        return schedule

    def _holes_per_8ms(self, schedule: list[dict[str, Any]]) -> dict[str, Any]:
        buckets = Counter(floor(item["delay_ms"] / 8) for item in schedule)
        return {
            "max_holes_per_8ms": max(buckets.values(), default=0),
            "holes_per_8ms": [
                {
                    "window_start_ms": bucket * 8,
                    "window_end_ms": bucket * 8 + 7,
                    "hole_count": count,
                }
                for bucket, count in sorted(buckets.items())
            ],
        }

    def _score(self, schedule: list[dict[str, Any]]) -> dict[str, Any]:
        counts = Counter(item["delay_ms"] for item in schedule)
        max_per_delay = max(counts.values(), default=0)
        duplicate_delays = sum(1 for c in counts.values() if c > 1)
        total_colliding_holes = sum(c - 1 for c in counts.values() if c > 1)
        per_8 = self._holes_per_8ms(schedule)
        return {
            "max_holes_per_delay": max_per_delay,
            "duplicate_delay_count": duplicate_delays,
            "colliding_holes": total_colliding_holes,
            **per_8,
        }

    def _validate_rows(self, rows: list[dict[str, Any]], hole_ids: set[str]) -> None:
        seen: set[str] = set()
        for idx, row in enumerate(rows, start=1):
            for hole_id in row.get("hole_ids", []):
                hole_id = str(hole_id)
                if hole_id not in hole_ids:
                    raise ValueError(
                        f"Row {idx}: hole id {hole_id} not found in uploaded holes"
                    )
                if hole_id in seen:
                    raise ValueError(f"Hole id {hole_id} appears in multiple rows")
                seen.add(hole_id)

    def optimize(self, blast_data) -> dict[str, Any]:
        holes = blast_data.holes
        rows = blast_data.rows
        constraints = self._parse_constraints(blast_data.constraints)

        if not rows:
            raise ValueError("No row assignments provided")

        self._validate_rows(rows, {str(h["id"]) for h in holes})

        candidates: list[dict[str, Any]] = []
        for hole_delay in range(
            constraints["hole_to_hole_min"], constraints["hole_to_hole_max"] + 1
        ):
            for row_delay in range(
                constraints["row_to_row_min"], constraints["row_to_row_max"] + 1
            ):
                schedule = self._build_schedule(rows, hole_delay, row_delay)
                score = self._score(schedule)
                candidates.append(
                    {
                        "hole_delay_ms": hole_delay,
                        "row_delay_ms": row_delay,
                        "timing": schedule,
                        "metrics": score,
                    }
                )

        if not candidates:
            raise ValueError("No feasible timing solution found")

        candidates.sort(
            key=lambda c: (
                c["metrics"]["max_holes_per_delay"],
                c["metrics"]["max_holes_per_8ms"],
                c["metrics"]["colliding_holes"],
                c["metrics"]["duplicate_delay_count"],
                c["hole_delay_ms"] + c["row_delay_ms"],
            )
        )

        best = candidates[0]

        conflicts = [
            {"delay_ms": delay, "hole_count": count}
            for delay, count in Counter(i["delay_ms"] for i in best["timing"]).items()
            if count > 1
        ]

        options = [
            {
                "option_id": idx + 1,
                "hole_to_hole_ms": c["hole_delay_ms"],
                "row_to_row_ms": c["row_delay_ms"],
                "metrics": c["metrics"],
                "timing": c["timing"],
            }
            for idx, c in enumerate(candidates[:20])
        ]

        return {
            "timing": best["timing"],
            "conflicts": sorted(conflicts, key=lambda x: x["delay_ms"]),
            "metrics": {
                **best["metrics"],
                "selected_hole_to_hole_ms": best["hole_delay_ms"],
                "selected_row_to_row_ms": best["row_delay_ms"],
            },
            "options": options,
        }
