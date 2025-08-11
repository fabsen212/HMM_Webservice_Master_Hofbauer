import sys
import subprocess
import os
from pathlib import Path

def run_hmmsearch(hmm_file, protein_file, e_value, coverage, min_length, result_dir="results"):
    basename = Path(protein_file).stem  # z.B. "Amborella_trichopoda"
    result_file = os.path.join(result_dir, f"hmmsearch_{basename}.txt")
    filtered_file = result_file.replace(".txt", "_filtered.txt")
    found_genes_file = os.path.join(result_dir, f"found_genes_{basename}.txt")
    log_file = os.path.join(result_dir, "analysis.log")

    os.makedirs(result_dir, exist_ok=True)

    # Step 1: Run hmmsearch
    with open(log_file, "a") as log:
        log.write(f"\nRunning hmmsearch on {protein_file} with model {hmm_file}\n")
        subprocess.run([
            "hmmsearch", "--domtblout", result_file, "-E", e_value,
            hmm_file, protein_file
        ], stdout=log, stderr=log, check=True)

    # Step 2: Extract HMM length
    hmm_length = None
    with open(hmm_file, "r") as f:
        for line in f:
            if line.startswith("LENG"):
                hmm_length = int(line.strip().split()[-1])
                break
    if hmm_length is None:
        raise ValueError("Could not determine HMM length.")

    # Step 3: Filter results and collect gene IDs
    accepted_genes = set()
    with open(result_file, "r") as infile, \
         open(filtered_file, "w") as outfile, \
         open(found_genes_file, "w") as gene_out:

        for line in infile:
            if line.startswith("#"):
                continue
            parts = line.strip().split()
            try:
                env_from = int(parts[17])
                env_to = int(parts[18])
                dom_len = abs(env_to - env_from) + 1
                cov = (dom_len / hmm_length) * 100
                if cov >= float(coverage) and dom_len >= int(min_length):
                    outfile.write(line + "\n")
                    gene_out.write(parts[0] + "\n")
                    accepted_genes.add(parts[0])
            except (ValueError, IndexError):
                continue

    with open(log_file, "a") as log:
        log.write(f"Filtered results saved in {filtered_file}\n")
        log.write(f"Found {len(accepted_genes)} genes after filtering.\n")
        if len(accepted_genes) == 0:
            log.write("No genes passed the filter. Consider lowering coverage or min_length.\n")
        else:
            log.write(f"Gene IDs written to {found_genes_file}\n")

if __name__ == "__main__":
    hmm_file = sys.argv[1]
    protein_file = sys.argv[2]
    e_value = sys.argv[3]
    coverage = sys.argv[4]
    min_length = sys.argv[5]
    result_dir = sys.argv[6]
    run_hmmsearch(hmm_file, protein_file, e_value, coverage, min_length, result_dir)
