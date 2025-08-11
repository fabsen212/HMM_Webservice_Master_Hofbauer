import os
import json
import subprocess

def improved_sanitize_and_save_fasta(aligned_fasta, output_fasta):
    sanitized_lines = []
    header_mapping = {}
    counter = 1

    with open(aligned_fasta, "r") as f:
        for line in f:
            if line.startswith(">"):
                raw_header = line.strip()[1:]
                if raw_header.startswith("seq") and "_" in raw_header:
                    parts = raw_header.split("_", 1)
                    if parts[0].startswith("seq") and parts[0][3:].isdigit():
                        raw_header = parts[1]
                safe_header = raw_header.replace('|', '__').replace(':', '--').replace(' ', '_')
                new_id = f"seq{counter}_{safe_header}"
                sanitized_lines.append(f">{new_id}")
                header_mapping[new_id] = raw_header
                counter += 1
            else:
                sanitized_lines.append(line.strip())

    with open(output_fasta, "w") as f:
        f.write("\n".join(sanitized_lines))

    mapping_file = os.path.join(os.path.dirname(output_fasta), "fasta_header_mapping.json")
    with open(mapping_file, "w") as mf:
        json.dump(header_mapping, mf, indent=4)

    with open(os.path.join(os.path.dirname(output_fasta), "analysis.log"), "a") as log:
        log.write(f"FASTA file written: {output_fasta}\n")
        log.write(f"Mapping saved: {mapping_file}\n")
    return output_fasta

def run_fasttree_protein(aligned_fasta, output_tree=None):
    if output_tree is None:
        output_tree = os.path.join(os.path.dirname(aligned_fasta), 'phylo_tree.nwk')

    if not os.path.exists(aligned_fasta) or os.path.getsize(aligned_fasta) == 0:
        with open(os.path.join(os.path.dirname(aligned_fasta), "analysis.log"), "a") as log:
            log.write(f"File {aligned_fasta} not found or empty\n")
        return None

    result_dir = os.path.dirname(aligned_fasta)
    cleaned_fasta = os.path.join(result_dir, "aligned_cleaned_strict.fasta")
    improved_sanitize_and_save_fasta(aligned_fasta, cleaned_fasta)

    log_file = os.path.join(result_dir, "analysis.log")
    try:
        with open(log_file, "a") as log:
            log.write(f"Start FastTree with {cleaned_fasta}...\n")
            with open(output_tree, "w") as out:
                subprocess.run(["FastTree", "-lg", cleaned_fasta], stdout=out, stderr=log, check=True)
            log.write(f"FastTree tree saved: {output_tree}\n")
        return output_tree
    except subprocess.CalledProcessError as e:
        with open(log_file, "a") as log:
            log.write(f"Error with FastTree: {e}\n")
        return None
