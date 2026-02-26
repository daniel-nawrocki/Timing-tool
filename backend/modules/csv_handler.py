from __future__ import annotations

import csv
import io
from typing import Any


class CSVHandler:
    """Parse and export blast hole/timing CSV files."""

    REQUIRED_ALIASES = {
        "id": {"id", "hole_id", "hole", "holeid"},
        "x": {"x", "east", "easting", "x_coord", "xcoordinate"},
        "y": {"y", "north", "northing", "y_coord", "ycoordinate"},
    }

    def _normalize_header(self, header: str) -> str:
        return header.strip().lower().replace(" ", "_")

    def _resolve_columns(self, fieldnames: list[str]) -> dict[str, str]:
        normalized = {self._normalize_header(h): h for h in fieldnames}
        resolved: dict[str, str] = {}

        for key, aliases in self.REQUIRED_ALIASES.items():
            match = next((normalized[a] for a in aliases if a in normalized), None)
            if match is None:
                raise ValueError(
                    f"Missing required column for '{key}'. Expected one of: {sorted(aliases)}"
                )
            resolved[key] = match

        return resolved

    def parse_csv(self, file_storage) -> list[dict[str, Any]]:
        """Parse uploaded CSV and return normalized hole records."""
        content = file_storage.read()
        if isinstance(content, bytes):
            text = content.decode("utf-8-sig")
        else:
            text = str(content)

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValueError("CSV is empty or missing header row")

        columns = self._resolve_columns(reader.fieldnames)
        holes: list[dict[str, Any]] = []

        for idx, row in enumerate(reader, start=2):
            try:
                hole_id = str(row[columns["id"]]).strip()
                x_val = float(row[columns["x"]])
                y_val = float(row[columns["y"]])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid numeric value at CSV line {idx}: {exc}") from exc

            if not hole_id:
                raise ValueError(f"Missing hole id at CSV line {idx}")

            extras = {
                k: v for k, v in row.items() if k not in {columns["id"], columns["x"], columns["y"]}
            }
            holes.append({"id": hole_id, "x": x_val, "y": y_val, "attributes": extras})

        if not holes:
            raise ValueError("CSV contains no hole records")

        return holes

    def export_timing(self, timing_rows: list[dict[str, Any]]) -> str:
        """Export timing assignments to CSV string."""
        if not timing_rows:
            raise ValueError("No timing data to export")

        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "hole_id",
                "row_id",
                "position_in_row",
                "delay_ms",
                "row_reference_hole",
            ],
        )
        writer.writeheader()
        writer.writerows(timing_rows)
        return output.getvalue()
