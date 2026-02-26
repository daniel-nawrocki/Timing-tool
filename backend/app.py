from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
from modules.csv_handler import CSVHandler
from modules.optimizer import TimingOptimizer
from modules.models import BlastData

app = Flask(__name__)
CORS(app)

# Initialize handlers
csv_handler = CSVHandler()
optimizer = TimingOptimizer()

@app.route('/', methods=['GET'])
def index():
    return send_from_directory('static', 'index.html')


@app.route("/api/upload", methods=["POST"])
def upload_csv():
    """Handle CSV file upload and parsing"""
    try:
        if "file" not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"error": "No file selected"}), 400

        if not file.filename.endswith(".csv"):
            return jsonify({"error": "File must be CSV"}), 400

        # Parse CSV
        holes_data = csv_handler.parse_csv(file)

        return (
            jsonify(
                {"status": "success", "holes": holes_data, "count": len(holes_data)}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/optimize", methods=["POST"])
def optimize_timing():
    """Calculate optimal timing to minimize holes firing within 8ms"""
    try:
        data = request.get_json()

        if not data or "holes" not in data:
            return jsonify({"error": "No holes data provided"}), 400

        holes = data["holes"]
        rows = data.get("rows", [])
        offsets = data.get("offsets", {})

        # Create BlastData object
        blast_data = BlastData(holes=holes, rows=rows, offsets=offsets)

        # Run optimization
        result = optimizer.optimize(blast_data)

        return (
            jsonify(
                {
                    "status": "success",
                    "timing": result["timing"],
                    "conflicts": result["conflicts"],
                    "metrics": result["metrics"],
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/validate", methods=["POST"])
def validate_data():
    """Validate holes and row configuration"""
    try:
        data = request.get_json()

        if not data or "holes" not in data:
            return jsonify({"error": "No holes data provided"}), 400

        holes = data["holes"]
        rows = data.get("rows", [])

        # Validate
        errors = []
        if len(holes) == 0:
            errors.append("No holes defined")

        if rows:
            for row_idx, row in enumerate(rows):
                for hole_id in row.get("hole_ids", []):
                    if hole_id not in [h["id"] for h in holes]:
                        errors.append(f"Row {row_idx}: Hole {hole_id} not found")

        if errors:
            return jsonify({"status": "invalid", "errors": errors}), 400

        return jsonify({"status": "valid", "message": "Data is valid"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/export", methods=["POST"])
def export_timing():
    """Export timing results as CSV"""
    try:
        data = request.get_json()

        if not data or "timing" not in data:
            return jsonify({"error": "No timing data provided"}), 400

        csv_content = csv_handler.export_timing(data["timing"])

        return jsonify({"status": "success", "csv": csv_content}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)

