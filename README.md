diff --git a/README.md b/README.md
index e69de29bb2d1d6434b8b29ae775ad8c2e48c5391..b957a2a60804a17a190a606c40c98b0c6bf00afa 100644
--- a/README.md
+++ b/README.md
@@ -0,0 +1,63 @@
+# Timing Tool
+
+Backend + visual UI for quarry blast timing optimization.
+
+## What it does
+
+- Imports blast holes from CSV (`id`, `x`, `y`, plus optional extra columns).
+- Lets you click or drag-select holes into rows on a hole diagram.
+- Solves timing options across user-defined hole-to-hole and row-to-row ranges.
+- Shows selectable timing options in real time and updates delay labels on holes instantly.
+- Exports CSV including:
+  - selected hole-to-hole timing,
+  - selected row-to-row timing,
+  - holes-per-8ms summary,
+  - full hole delay table.
+
+## Run
+
+```bash
+cd backend
+pip install -r requirements.txt
+python app.py
+```
+
+Open `http://127.0.0.1:5000`.
+
+## API
+
+### `POST /api/upload`
+Form-data with key `file`.
+
+### `POST /api/optimize`
+Payload:
+
+```json
+{
+  "holes": [{"id": "H1", "x": 100.0, "y": 200.0}],
+  "rows": [
+    {"row_id": 1, "hole_ids": ["H1", "H2"], "start_from_prev_hole": 1},
+    {"row_id": 2, "hole_ids": ["H3", "H4"], "start_from_prev_hole": 3}
+  ],
+  "constraints": {
+    "hole_to_hole_min": 9,
+    "hole_to_hole_max": 25,
+    "row_to_row_min": 17,
+    "row_to_row_max": 42
+  }
+}
+```
+
+Returns best `timing` + ranked `options` (first 20).
+
+### `POST /api/export`
+Payload:
+
+```json
+{
+  "timing": [...],
+  "summary": [
+    {"section": "timings", "name": "row_1_hole_to_hole_ms", "value": 17}
+  ]
+}
+```
