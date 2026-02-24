import csv

class CSVHandler:
    def __init__(self, column_mapping=None):
        # Initialize with a mapping provided by the user
        self.column_mapping = column_mapping or {}

    def read_csv(self, file_path):
        with open(file_path, mode='r', encoding='utf-8') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            for row in csv_reader:
                self.process_row(row)

    def process_row(self, row):
        # Map the row using the column_mapping provided
        mapped_row = {self.column_mapping.get(key, key): value for key, value in row.items()}
        # Perform operations on the mapped row
        print(mapped_row)  # Replace with actual processing logic

    def write_csv(self, file_path, data):
        with open(file_path, mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = self.column_mapping.values()  # Use mapped values for header
            csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            csv_writer.writeheader()
            for item in data:
                csv_writer.writerow({self.column_mapping.get(key, key): value for key, value in item.items()})
