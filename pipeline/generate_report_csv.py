import csv
import os
import sys

def generate_csv_report(result_files, result_dir):
    output_csv = os.path.join(result_dir, 'report.csv')
    """Saves the results as a CSV file."""
    
    if not result_files:
        print("❌ No result files found!")
        return

    with open(output_csv, "w", newline="", encoding="utf-8") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["File", "Result"])  # Kopfzeile

        for file_name in result_files:
            file_path = os.path.join(result_dir, file_name)
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[:]
                    for line in lines:
                        csvwriter.writerow([file_name, line.strip()])

    print(f"✅ CSV report saved: {output_csv}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Error: No result files transferred!")
        sys.exit(1)

    result_files = sys.argv[1:]
    generate_csv_report(result_files)
