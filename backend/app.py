from flask import Flask, request, jsonify
from flask_cors import CORS

from modules.csv_handler import CSVHandler
from modules.optimizer import TimingOptimizer
from modules.models import BlastData

app = Flask(__name__)
CORS(app)

csv_handler = CSVHandler()
optimizer = TimingOptimizer()


@app.route('/api/upload', methods=['POST'])
def upload_csv():
    """Handle CSV file upload and parsing."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not file.filename.lower().endswith('.csv'):
            return jsonify({'error': 'File must be CSV'}), 400

        holes_data = csv_handler.parse_csv(file)

        return jsonify({'status': 'success', 'holes': holes_data, 'count': len(holes_data)}), 200

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/optimize', methods=['POST'])
def optimize_timing():
    """Calculate optimal timing to minimize holes sharing a delay."""
    try:
        data = request.get_json()

        if not data or 'holes' not in data:
            return jsonify({'error': 'No holes data provided'}), 400

        blast_data = BlastData(
            holes=data['holes'],
            rows=data.get('rows', []),
            constraints=data.get('constraints', {}),
        )

        result = optimizer.optimize(blast_data)

        return jsonify(
            {
                'status': 'success',
                'timing': result['timing'],
                'conflicts': result['conflicts'],
                'metrics': result['metrics'],
            }
        ), 200

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/validate', methods=['POST'])
def validate_data():
    """Validate holes and row configuration."""
    try:
        data = request.get_json()

        if not data or 'holes' not in data:
            return jsonify({'error': 'No holes data provided'}), 400

        holes = data['holes']
        rows = data.get('rows', [])

        errors = []
        if not holes:
            errors.append('No holes defined')

        hole_ids = {str(h['id']) for h in holes}
        assigned = set()

        for row_idx, row in enumerate(rows, start=1):
            start_ref = int(row.get('start_from_prev_hole', 1))
            if start_ref < 1:
                errors.append(f'Row {row_idx}: start_from_prev_hole must be >= 1')

            for hole_id in row.get('hole_ids', []):
                hole_id = str(hole_id)
                if hole_id not in hole_ids:
                    errors.append(f'Row {row_idx}: Hole {hole_id} not found')
                if hole_id in assigned:
                    errors.append(f'Row {row_idx}: Hole {hole_id} assigned more than once')
                assigned.add(hole_id)

        if errors:
            return jsonify({'status': 'invalid', 'errors': errors}), 400

        return jsonify({'status': 'valid', 'message': 'Data is valid'}), 200

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/api/export', methods=['POST'])
def export_timing():
    """Export timing results as CSV."""
    try:
        data = request.get_json()

        if not data or 'timing' not in data:
            return jsonify({'error': 'No timing data provided'}), 400

        csv_content = csv_handler.export_timing(data['timing'])
        return jsonify({'status': 'success', 'csv': csv_content}), 200

    except Exception as exc:
        return jsonify({'error': str(exc)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy'}), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
