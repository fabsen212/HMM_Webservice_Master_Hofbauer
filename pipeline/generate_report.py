from fpdf import FPDF
import os

def generate_report(input_folder, output_pdf=None):
    if output_pdf is None:
        output_pdf = os.path.join(input_folder, 'report.pdf')
    if not os.path.exists(input_folder):
        print(f"Folder '{input_folder}' does not exist!")
        return

    text_files = [f for f in os.listdir(input_folder) if f.endswith(".txt")]
    
    if not text_files:
        print(f"No .txt files found in ‘{input_folder}")
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "HMM Analysis Report", ln=True, align="C")
    pdf.ln(10)

    for file_name in text_files:
        file_path = os.path.join(input_folder, file_name)
        print(f"Process file:{file_path}")

        if os.path.exists(file_path):
            pdf.set_font("Arial", "B", 12)
            pdf.cell(200, 10, f"Results from {file_name}:", ln=True)
            pdf.ln(5)
            pdf.set_font("Arial", size=10)

            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()[:30]
                for line in lines:
                    pdf.multi_cell(0, 5, line.strip())
                    pdf.ln(1)

    pdf.output(output_pdf)
    print(f"PDF report saved: {output_pdf}")

if __name__ == "__main__":
    generate_report()
