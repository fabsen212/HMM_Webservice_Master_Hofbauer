import requests
import os
import sys

def download_hmm_from_pfam(pfam_id, save_dir="uploads"):
    """
    Downloads an HMM file from the InterPro website and unpacks it.
    """
    api_url = f"https://www.ebi.ac.uk/interpro/wwwapi/entry/pfam/{pfam_id}?annotation=hmm"
    save_path_gz = os.path.join(save_dir, f"{pfam_id}.hmm.gz")
    save_path = os.path.join(save_dir, f"{pfam_id}.hmm")

    try:
        response = requests.get(api_url, stream=True)
        if response.status_code == 200:
            os.makedirs(save_dir, exist_ok=True)
            with open(save_path_gz, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Datei entpacken mit `gunzip`
            os.system(f"gunzip -c {save_path_gz} > {save_path}")
            os.remove(save_path_gz)

            # Return of the actual file path
            if os.path.exists(save_path):
                print(save_path)  # IMPORTANT: ONLY output the pure path!
                return save_path
            else:
                print("ERROR")
                return None
        else:
            print("ERROR")
            return None
    except Exception:
        print("ERROR")
        return None

if __name__ == "__main__":
    pfam_id = sys.argv[1]
    hmm_path = download_hmm_from_pfam(pfam_id)

    if hmm_path:
        print(hmm_path)  # IMPORTANT: ONLY output the pure path!
    else:
        print("ERROR")
