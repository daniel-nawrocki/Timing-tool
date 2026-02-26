# Timing Tool

Backend service for quarry blast timing optimization.

## What it does

- Imports blast holes from CSV (`id`, `x`, `y`, plus optional extra columns).
- Accepts user-defined row assignments with ordered hole IDs and row alignment offsets (`start_from_prev_hole`).
- Finds hole-to-hole and row-to-row delays within user min/max ranges that minimize holes sharing the same delay.
- Exports optimized delays to CSV.

## Run

```bash
cd backend
pip install -r requirements.txt
python app.py
```

## API

### `POST /api/upload`
Form-data with file key `file`.

### `POST /api/validate`
```json
{
  "holes": [{"id": "H1", "x": 100.0, "y": 200.0}],
  "rows": [
    {"row_id": 1, "hole_ids": ["H1", "H2"], "start_from_prev_hole": 1},
    {"row_id": 2, "hole_ids": ["H3", "H4"], "start_from_prev_hole": 3}
  ]
}
```

### `POST /api/optimize`
```json
{
  "holes": [{"id": "H1", "x": 100.0, "y": 200.0}],
  "rows": [
    {"row_id": 1, "hole_ids": ["H1", "H2"], "start_from_prev_hole": 1},
    {"row_id": 2, "hole_ids": ["H3", "H4"], "start_from_prev_hole": 3}
  ],
  "constraints": {
    "hole_to_hole_min": 9,
    "hole_to_hole_max": 25,
    "row_to_row_min": 17,
    "row_to_row_max": 42
  }
}
```

### `POST /api/export`
```json
{
  "timing": [
    {
      "hole_id": "H1",
      "row_id": 1,
      "position_in_row": 1,
      "delay_ms": 0,
      "row_reference_hole": 1
    }
  ]
}
```
