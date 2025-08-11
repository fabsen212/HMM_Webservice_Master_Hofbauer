import os
import subprocess

def extract_combined_sequences(result_dir="results", protein_dir="database/proteins"):
    log_path = os.path.join(result_dir, "analysis.log")
    with open(log_path, "a") as log:
        if not os.path.exists(result_dir):
            log.write(f"Results folder {result_dir} does not exist!\n")
            return None

        found_genes = set()
        for file in os.listdir(result_dir):
            if file.endswith("_filtered.txt"): 
                with open(os.path.join(result_dir, file)) as f:
                    for line in f:
                        if not line.startswith("#"):
                            parts = line.strip().split()
                            if parts:
                                found_genes.add(parts[0])

        if not found_genes:
            log.write("No filtered hits found!!\n")
            return None

        gene_list_file = os.path.join(result_dir, "found_genes.txt")
        with open(gene_list_file, "w") as f:
            f.writelines([gene + "\n" for gene in sorted(found_genes)])

        combined_fasta = os.path.join(result_dir, "combined_sequences.faa")
        with open(combined_fasta, "w") as out:
            for faa_file in os.listdir(protein_dir):
                if faa_file.endswith(".faa"):
                    path = os.path.join(protein_dir, faa_file)
                    os.system(f"seqkit grep -f {gene_list_file} {path} >> {combined_fasta}")

        if not os.path.exists(combined_fasta) or os.path.getsize(combined_fasta) == 0:
            log.write("No sequences extracted!\n")
            return None

        log.write(f"Sequences are merged in: {combined_fasta}\n")
        return combined_fasta

def run_mafft(fasta_file):
    aligned_file = os.path.join(os.path.dirname(fasta_file), "aligned.fasta")
    log_path = os.path.join(os.path.dirname(fasta_file), "analysis.log")
    with open(log_path, "a") as log:
        if not os.path.exists(fasta_file) or os.path.getsize(fasta_file) == 0:
            log.write(f"Input file {fasta_file} does not exist or is empty!\n")
            return None

        try:
            log.write(f"Starting MAFFT on {fasta_file}...\n")
            with open(aligned_file, 'w') as out:
                subprocess.run(["mafft", "--auto", fasta_file], stdout=out, stderr=log, check=True)
            log.write(f"MAFFT completed: {aligned_file}\n")
            return aligned_file
        except subprocess.CalledProcessError as e:
            log.write(f"Error at MAFFT: {e}\n")
            return None

if __name__ == "__main__":
    test_dir = "results/testuser"
    extracted = extract_combined_sequences(result_dir=test_dir)
    if extracted:
        run_mafft(extracted)
