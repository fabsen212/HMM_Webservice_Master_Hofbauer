import os
import contextlib
from pipeline.run_hmmsearch import run_hmmsearch
from pipeline.run_mafft import run_mafft, extract_combined_sequences
from pipeline.run_phylo import run_fasttree_protein, improved_sanitize_and_save_fasta
from pipeline.generate_report import generate_report
from pipeline.generate_report_csv import generate_csv_report
from pipeline.download_hmm_from_pfam import download_hmm_from_pfam


# Kontextmanager zum Umleiten von stdout/stderr in analysis.log
@contextlib.contextmanager
def log_all_output(result_dir):
    os.makedirs(result_dir, exist_ok=True)
    log_path = os.path.join(result_dir, "analysis.log")
    with open(log_path, "a") as f:
        with contextlib.redirect_stdout(f), contextlib.redirect_stderr(f):
            print("\n" + "=" * 60)
            print(f"New task started in {result_dir}")
            yield
            print(f"Task finished in {result_dir}")
            print("=" * 60 + "\n")


def run_hmmsearch_task(hmm_path, protein_path, e_value="1e-5", coverage="100", min_length="50", result_dir="results"):
    with log_all_output(result_dir):
        print(f"Start HMM search: {os.path.basename(protein_path)}")
        print(f"Filter: E={e_value}, Coverage={coverage}, Min Length={min_length}")
        run_hmmsearch(hmm_path, protein_path, e_value, coverage, min_length, result_dir)
        print("HMM search finished\n")
    return "done"


def run_mafft_task(result_dir):
    with log_all_output(result_dir):
        print("Start MAFFT Alignment...")
        combined_path = os.path.join(result_dir, "combined_sequences.faa")
        if os.path.exists(combined_path):
            os.remove(combined_path)

        combined = extract_combined_sequences(result_dir=result_dir)
        if not combined:
            print("No Sequences founded – Alignment failed")
            return "error"

        result = run_mafft(combined)
        print("MAFFT finished\n")
        return result or "error"


def run_phylo_tree(aligned_fasta):
    result_dir = os.path.dirname(aligned_fasta)
    with log_all_output(result_dir):
        print(f"Start phylogeny creation based on: {aligned_fasta}")
        cleaned_fasta = os.path.join(result_dir, "aligned_cleaned_strict.fasta")

        for file in ["phylo_tree.nwk", "tree_ascii.txt", "tree_output.png"]:
            path = os.path.join(result_dir, file)
            if os.path.exists(path):
                os.remove(path)

        improved_sanitize_and_save_fasta(aligned_fasta, cleaned_fasta)
        print("FASTA cleaned – FastTree is started...")

        newick = run_fasttree_protein(cleaned_fasta)
        if newick:
            print("Tree successfully created\n")
            return "done"
        else:
            print("Error: FastTree could not create a tree\n")
            return "error"


def generate_pdf_report_task(result_dir):
    with log_all_output(result_dir):
        print(f"Create PDF report for: {result_dir}")
        generate_report(input_folder=result_dir)
        print("PDF report completed\n")
    return "done"


def generate_csv_report_task(files, result_dir):
    with log_all_output(result_dir):
        print(f"Create CSV report for files: {files}")
        generate_csv_report(files, result_dir)
        print("CSV report completed\n")
    return "done"


def download_hmm_task(pfam_id):
    # Diese Funktion lädt nur – kein result_dir vorhanden
    print(f"Load HMM from Pfam: {pfam_id}")
    return download_hmm_from_pfam(pfam_id)

