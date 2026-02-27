from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from modules.csv_handler import CSVHandler
from modules.optimizer import TimingOptimizer
from modules.models import BlastData

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)

csv_handler = CSVHandler()
optimizer = TimingOptimizer()


def _normalize_constraints(payload: dict | None) -> dict[str, int]:
    """Accept legacy/alias constraint keys and return canonical keys."""

    source = payload or {}

    def first_value(*keys):
        for key in keys:
            if key in source and source[key] is not None:
                return source[key]
        return None

    def nested_value(*paths):
        for group_key, value_key in paths:
            group = source.get(group_key)
            if isinstance(group, dict) and group.get(value_key) is not None:
                return group.get(value_key)
        return None

    hh_min = first_value("hole_to_hole_min", "holeToHoleMin", "hh_min")
    hh_max = first_value("hole_to_hole_max", "holeToHoleMax", "hh_max")
    rr_min = first_value("row_to_row_min", "rowToRowMin", "rr_min")
    rr_max = first_value("row_to_row_max", "rowToRowMax", "rr_max")

    # Support nested payload shapes like:
    # {"hole_to_hole": {"min": 9, "max": 12}, "row_to_row": {"min": 17, "max": 42}}
    if hh_min is None:
        hh_min = nested_value(("hole_to_hole", "min"), ("holeToHole", "min"))
    if hh_max is None:
        hh_max = nested_value(("hole_to_hole", "max"), ("holeToHole", "max"))
    if rr_min is None:
        rr_min = nested_value(("row_to_row", "min"), ("rowToRow", "min"))
    if rr_max is None:
        rr_max = nested_value(("row_to_row", "max"), ("rowToRow", "max"))

    # Support older/simpler payloads that only sent single values.
    hh_single = first_value("hole_to_hole", "holeToHole", "hole_delay", "holeDelay")
    rr_single = first_value("row_to_row", "rowToRow", "row_delay", "rowDelay")

    if hh_min is None:
        hh_min = hh_single
    if hh_max is None:
        hh_max = hh_single
    if rr_min is None:
        rr_min = rr_single
    if rr_max is None:
        rr_max = rr_single

    normalized = {
        "hole_to_hole_min": hh_min,
        "hole_to_hole_max": hh_max,
        "row_to_row_min": rr_min,
        "row_to_row_max": rr_max,
    }

    missing = [key for key, value in normalized.items() if value is None]
    if missing:
        raise ValueError(
            "Missing timing constraint values: "
            + ", ".join(missing)
            + ". Provide min/max hole-to-hole and row-to-row values."
        )

    return {key: int(value) for key, value in normalized.items()}


@app.route("/", methods=["GET"])
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/upload", methods=["POST"])
def upload_csv():
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.lower().endswith(".csv"):
            return jsonify({"error": "File must be CSV"}), 400

        holes_data = csv_handler.parse_csv(file)

        return (
            jsonify(
                {"status": "success", "holes": holes_data, "count": len(holes_data)}
            ),
            200,
        )

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/optimize", methods=["POST"])
def optimize_timing():
    try:
        data = request.get_json()

        if not data or "holes" not in data:
            return jsonify({"error": "No holes data provided"}), 400

        constraints = data.get("constraints")
        if not constraints and "offsets" in data:
            # Backward-compatible fallback for older clients still posting `offsets`.
            constraints = data.get("offsets")

        if not constraints:
            return (
                jsonify(
                    {
                        "error": "Missing timing constraints. Provide `constraints` with hole/row min/max values."
                    }
                ),
                400,
            )

        constraints = _normalize_constraints(constraints)

        blast_data = BlastData(
            holes=data["holes"],
            rows=data.get("rows", []),
            constraints=constraints,
        )

        result = optimizer.optimize(blast_data)

        timing = result.get("timing", [])
        conflicts = result.get("conflicts", [])
        metrics = result.get("metrics", {})
        options = result.get("options")

        if options is None:
            options = [
                {
                    "option_id": 1,
                    "hole_to_hole_ms": metrics.get("selected_hole_to_hole_ms"),
                    "row_to_row_ms": metrics.get("selected_row_to_row_ms"),
                    "metrics": metrics,
                    "timing": timing,
                }
            ]

        return (
            jsonify(
                {
                    "status": "success",
                    "timing": timing,
                    "conflicts": conflicts,
                    "metrics": metrics,
                    "options": options,
                }
            ),
            200,
        )

    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/validate", methods=["POST"])
def validate_data():
    try:
        data = request.get_json()

        if not data or "holes" not in data:
            return jsonify({"error": "No holes data provided"}), 400

        holes = data["holes"]
        rows = data.get("rows", [])

        errors = []
        if not holes:
            errors.append("No holes defined")

        hole_ids = {str(h["id"]) for h in holes}
        assigned = set()

        for row_idx, row in enumerate(rows, start=1):
            start_ref = int(row.get("start_from_prev_hole", 1))
            if start_ref < 1:
                errors.append(f"Row {row_idx}: start_from_prev_hole must be >= 1")

            for hole_id in row.get("hole_ids", []):
                hole_id = str(hole_id)
                if hole_id not in hole_ids:
                    errors.append(f"Row {row_idx}: Hole {hole_id} not found")
                if hole_id in assigned:
                    errors.append(
                        f"Row {row_idx}: Hole {hole_id} assigned more than once"
                    )
                assigned.add(hole_id)

        if errors:
            return jsonify({"status": "invalid", "errors": errors}), 400

        return jsonify({"status": "valid", "message": "Data is valid"}), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/export", methods=["POST"])
def export_timing():
    try:
        data = request.get_json()

        if not data or "timing" not in data:
            return jsonify({"error": "No timing data provided"}), 400

        csv_content = csv_handler.export_timing(
            data["timing"],
            summary_rows=data.get("summary", []),
        )
        return jsonify({"status": "success", "csv": csv_content}), 200

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
