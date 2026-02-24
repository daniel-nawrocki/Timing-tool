import csv

class CSVHandler:
    def __init__(self, filename):
        self.filename = filename

    def parse_blasting_hole_data(self):
        data = []
        with open(self.filename, mode='r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header
            for row in reader:
                data.append(self._parse_row(row))
        return data

    def _parse_row(self, row):
        # Assuming row has known structure, adjust according to actual data
        return {
            'hole_id': row[0],
            'depth': float(row[1]),
            'diameter': float(row[2]),
            'charge_type': row[3],
        }

    def export_blasting_hole_data(self, data, export_filename):
        with open(export_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['hole_id', 'depth', 'diameter', 'charge_type'])  # Header
            for row in data:
                writer.writerow([row['hole_id'], row['depth'], row['diameter'], row['charge_type']])
        
# Example usage: 
# handler = CSVHandler('blasting_holes.csv')
# data = handler.parse_blasting_hole_data()
# handler.export_blasting_hole_data(data, 'exported_blasting_holes.csv')
