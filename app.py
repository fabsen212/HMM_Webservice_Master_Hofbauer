######################################################################################### Configuration & Initialization #######################################################################################################
# Import necessary modules
import os  # Operating system tools and plotting library
import matplotlib, matplotlib.pyplot as plt  # Matplotlib plotting interface
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, session  # Web framework tools
from config import Config
from datetime import timedelta  # Used to control session timeout
from Bio import Phylo  # Used to work with phylogenetic trees
from werkzeug.utils import secure_filename  # Secures filenames of uploaded files
from flask_rq2 import RQ  # Flask integration for Redis Queue
from rq.job import Job  # RQ job object
from redis import Redis  # Redis client

# Import custom task functions from the 'tasks' module
from tasks import (
    run_hmmsearch_task,         
    run_mafft_task,             
    run_phylo_tree,             
    generate_pdf_report_task,   
    generate_csv_report_task,              
    download_hmm_task           
)

# Initialize the Flask application
app = Flask(__name__)
app.permanent_session_lifetime = timedelta(minutes=30)  
app.config.from_object(Config) 

# Initialize Redis Queue (RQ) with the Flask app
rq = RQ(app)  # Bind Redis Queue to Flask app
queue = rq.get_queue('app.rq')  # Access a named queue for background tasks
redis_conn = Redis()  # Create a raw Redis connection

# Ensure that the upload and result directories exist 
for folder in [app.config["UPLOAD_FOLDER"], app.config["RESULT_FOLDER"], app.config["PROTEIN_FOLDER"]]:
    os.makedirs(folder, exist_ok=True)  # Only create if it doesn't already exist

################################################################################################################################################################################################################################

############################################################################################### Application - Layout ###########################################################################################################
# Route for the home page
@app.route("/", methods=["GET"])
def home():
    return render_template("home.html")  

# Function to retrieve a sorted list of species from the protein folder
def get_species():
    return sorted([
        file.replace('.faa', '')  # Remove the file extension to get species name
        for file in os.listdir(app.config["PROTEIN_FOLDER"])
        if file.endswith('.faa')  # Consider only files with '.faa' extension
    ])

# Route for the search page
@app.route("/search", methods=["GET"])
def search():
    species = get_species()  # Get the list of species
    return render_template("search.html", species=species)  # Render the search page with species list


####################################################################################################################################################################################################################################

################################################################################################ Application Workflow ##############################################################################################################
# Route to handle file uploads and initiate analysis
# Route to handle file uploads and initiate analysis
@app.route("/upload", methods=["POST"])
def upload_file():
    custom_folder = request.form.get("custom_folder", "").strip()
    if not custom_folder:
        return "Please specify a storage folder.", 400

    folder = secure_filename(custom_folder)
    session["custom_folder"] = folder
    user_result_dir = os.path.join(app.config["RESULT_FOLDER"], folder)
    os.makedirs(user_result_dir, exist_ok=True)

    uploaded_files = request.files.getlist("file")
    pfam_id = request.form.get("pfam_id")

    selected_species = request.form.get("species", "").split(",")
    selected_species = [s.strip() for s in selected_species if s.strip()]

    run_alignment = request.form.get("run_alignment") == "on"
    run_phylo = request.form.get("run_phylo") == "on"

    e_value = request.form.get("eValue", "1e-5")
    coverage = request.form.get("coverage", "100")
    min_length = request.form.get("length", "50")

    if not uploaded_files and not pfam_id:
        return "Please upload a HMM file or enter a Pfam ID.", 400

    hmm_path = None
    for file in uploaded_files:
        filename = secure_filename(file.filename)
        if not filename:
            continue

        path = os.path.join(user_result_dir, filename)
        file.save(path)

        if filename.endswith(".hmm"):
            hmm_path = path

    if pfam_id:
        hmm_path = download_hmm_task(pfam_id)

    if not hmm_path or not os.path.exists(hmm_path):
        return "Error creating or downloading the HMM file.", 500

    jobs = []

    for species in selected_species:
        protein_file = os.path.join(app.config["PROTEIN_FOLDER"], f"{species}.faa")
        if not os.path.exists(protein_file):
            return f"{species}.faa not found.", 400

        job_hmm = queue.enqueue(
            run_hmmsearch_task,
            hmm_path, protein_file, e_value, coverage, min_length,
            user_result_dir
        )
        jobs.append(job_hmm.id)

    aligned_fasta = os.path.join(user_result_dir, "aligned.fasta")

    if run_alignment and run_phylo:
        job_mafft = queue.enqueue(run_mafft_task, user_result_dir, job_timeout=6000)
        job_tree = queue.enqueue(run_phylo_tree, aligned_fasta, depends_on=job_mafft, job_timeout=6000)
        jobs.extend([job_mafft.id, job_tree.id])
    elif run_alignment:
        job_mafft = queue.enqueue(run_mafft_task, user_result_dir, job_timeout=6000)
        jobs.append(job_mafft.id)
    elif run_phylo:
        return jsonify({
            "message": "Phylogenetic tree construction requires sequence alignment.",
            "status": "error",
            "error": "Please enable sequence alignment (MAFFT) when requesting tree generation."
        }), 400

    return jsonify({"message": "Analysis started.", "status": "processing", "jobs": jobs})



# 2. Upload a new plant (FASTA file) 
@app.route("/add_plant", methods=["POST"])
def add_plant():
    # Check if a file named "new_species" was included in the form submission
    if "new_species" not in request.files:
        return "No file uploaded.", 400  # Return error if no file was uploaded

    file = request.files.get("new_species")  # Get the uploaded file from the request
    if not file or file.filename == "":
        return "No file uploaded.", 400  # Return error if the file is empty

    filename = secure_filename(file.filename) 
    if not filename.endswith(".faa"):  # Only allow FASTA files with ".faa" extension
        return "Only .faa files are allowed.", 400

    # Define the target path to save the uploaded file
    save_path = os.path.join(app.config["PROTEIN_FOLDER"], filename)
    file.save(save_path)  # Save the file to the protein database folder
    print(f"New plant added: {save_path}")  # Log confirmation to the console

    return redirect(url_for("search"))  # Redirect back to the /search page

# 3. Delete a plant (species) file 
@app.route("/delete_plant", methods=["POST"])
def delete_plant():
    # Get the species name to be deleted from the submitted form
    species_to_delete = request.form.get("species_to_delete", "").strip()
    if not species_to_delete:
        return "No species selected.", 400  # Return error if no name was provided

    # Generate the filename from species name 
    filename = secure_filename(species_to_delete + ".faa")
    file_path = os.path.join(app.config["PROTEIN_FOLDER"], filename)  # Build full file path

    # Ensure the file exists and is within the PROTEIN_FOLDER (security check)
    if os.path.exists(file_path) and file_path.startswith(app.config["PROTEIN_FOLDER"]):
        os.remove(file_path)  # Delete the file
        print(f"Plant deleted: {filename}")  # Log confirmation
        return redirect(url_for("search"))  # Redirect back to search page
    else:
        return f"File {filename} not found.", 404  # Return error if file not found

    
#############################################################################################################################################################################################################################################

########################################################################################################## Render ASCII tree from Newick file ############################################################################################### 
    
# Function to render a phylogenetic tree and save it as an ASCII-Text and PNG-File
def render_tree_for_results(folder):
    matplotlib.use("Agg")

    tree_file = os.path.join(app.config["RESULT_FOLDER"], folder, "phylo_tree.nwk")
    output_png = os.path.join(app.config["RESULT_FOLDER"], folder, "tree_output.png")

    if not os.path.exists(tree_file):
        print(f"Tree file not found: {tree_file}")
        return None

    try:
        tree = Phylo.read(tree_file, "newick")
        if not getattr(tree,"rooted",False):
            tree.root_at_midpoint()
        
        if getattr(tree.root, "branch_length", None) in (None,0):
            tree.root.branch_length=0.02
        
        original_lengths = {}
        offset = 0.02
        power = 0.7

        for clade in tree.find_clades():
            if clade.branch_length:
                original_lengths[clade] = clade.branch_length
                clade.branch_length = (clade.branch_length + offset) ** power
        
        # Dynamic size
        n_leaves = len(tree.get_terminals())
        fig_width = 20  
        fig_height = max(6, n_leaves * 0.5)

        fig = plt.figure(figsize=(fig_width, fig_height), facecolor="white")
        axes = fig.add_subplot(1, 1, 1, facecolor="white")

        # Draw tree with original values as labels
        Phylo.draw(
            tree,
            axes=axes,
            do_show=False,
            branch_labels=lambda c: f"{original_lengths.get(c, 0):.3f}" if c in original_lengths else ""
        )
        # Stil
        axes.set_ylabel("")
        axes.set_yticks([])
        axes.tick_params(left=False)
        for side in ["top", "left", "right"]:
            axes.spines[side].set_visible(False)
        axes.spines["bottom"].set_color("black")

        # Calculate the actual path length to each leaf
        depths = tree.depths()
        max_depth = max(depths.values())

        # X-axis incl. buffer for labels on the right
        xmax = max_depth + 1.5
        axes.set_xlim(0, xmax)
        xticks = np.arange(0, xmax + 0.25, 0.25)
        axes.set_xticks(xticks)
        for label in axes.get_yticklabels():
            label.set_fontsize(9)

        axes.axvline(0,ymin=0,ymax=1,linewidth=0.8, color="#555555",alpha=0.7)
        
        plt.tight_layout()
        plt.savefig(output_png, dpi=300, bbox_inches="tight")
        plt.close()

        return f"{folder}/tree_output.png"

    except Exception as e:
        print(f"Error rendering tree: {e}")
        return None

#################################################################################################################################################################################################################################################

############################################################################################################# Visualization results #############################################################################################################S
# Route to display results page in the browser
@app.route('/results')
def show_results():
    folder = session.get("custom_folder") or request.args.get("folder")  # Get folder from session or URL parameter
    if not folder:
        return "No analysis folder specified!", 400  # Error if no folder was provided

    session["custom_folder"] = folder  # Store the folder name back in session (persistent between pages)

    tree_image = render_tree_for_results(folder)  # Generate/render the phylogenetic tree
    return render_template('results.html', tree_image=tree_image)  # Render the results HTML with the tree image path

# Route to fetch analysis results in JSON format
@app.route('/get_results')
def get_results():
    folder = session.get("custom_folder")
    if not folder:
        return jsonify({"error": "No storage folder specified."}), 400

    user_result_dir = os.path.join(app.config["RESULT_FOLDER"], folder)
    results_data = {}

    combined_file = os.path.join(user_result_dir, "found_genes.txt")
    if os.path.exists(combined_file):
        with open(combined_file, "r") as f:
            results_data["All Combined Found Genes"] = [line.strip() for line in f if line.strip()]

    for fname in sorted(os.listdir(user_result_dir)):
        if fname.startswith("found_genes_") and fname.endswith(".txt") and fname != "found_genes.txt":
            species = fname.replace("found_genes_", "").replace(".txt", "")
            with open(os.path.join(user_result_dir, fname), "r") as f:
                results_data[f"Found in {species}"] = [line.strip() for line in f if line.strip()]

    return jsonify(results_data)

# Route to serve static result files from the result folder (e.g., tree_output.png or alignment files)
@app.route('/results_file/<path:filename>')
def serve_result_file(filename):
    file_path = os.path.join(app.config["RESULT_FOLDER"], filename)  # Build the full file path from result folder
    if os.path.exists(file_path):
        return send_file(file_path)  # Send file to browser for display/download
    return "File not found", 404  

#########################################################################################################################################################################################################################################################

####################################################################################################### Report generation (PDF/CSV/Newick) ##############################################################################################################
# Route to generate a combined report (PDF or CSV) asynchronously via Redis queue
@app.route('/generate_report_combined', methods=['POST'])
def generate_report_combined():
    folder = session.get("custom_folder")  # Retrieve the user's result folder from the session
    if not folder:
        return jsonify({"error": "No storage folder specified."}), 400  # Error if no folder is set

    user_result_dir = os.path.join(app.config["RESULT_FOLDER"], folder)  # Path to result directory
    format = request.form.get("format")  # Get the requested output format from the form (pdf or csv)

    if format == "csv":
        result_files = [f for f in os.listdir(user_result_dir) if f.endswith(".txt")]  # List all .txt result files
        if not result_files:
            return jsonify({"error": "No result files found."}), 404  # Error if no input files

        # Enqueue a task to generate a CSV report from multiple result files
        job = queue.enqueue(generate_csv_report_task, result_files, user_result_dir)
        return jsonify({"job_id": job.id, "format": "csv"})  # Return job ID to frontend

    else:
        # Enqueue a task to generate a PDF report from all results
        job = queue.enqueue(generate_pdf_report_task, user_result_dir)
        return jsonify({"job_id": job.id, "format": "pdf"})  # Return job ID to frontend


# Route to download the CSV report if it exists
@app.route("/download_csv")
def download_csv():
    folder = session.get("custom_folder")  # Get current result folder from session
    if not folder:
        return "No storage folder specified.", 400  # Return error if not set

    csv_path = os.path.join(app.config["RESULT_FOLDER"], folder, "report.csv")  # Path to the CSV report
    if os.path.exists(csv_path):
        return send_file(csv_path, as_attachment=True)  # Return the file as download attachment
    return "CSV report not found.", 404  # Error if the file doesn't exist


# Route to download the PDF report if it exists
@app.route("/download_report")
def download_report():
    folder = session.get("custom_folder")  # Get current result folder from session
    if not folder:
        return "No storage folder specified.", 400  # Error if missing

    report_path = os.path.join(app.config["RESULT_FOLDER"], folder, "report.pdf")  # Path to PDF report
    if os.path.exists(report_path):
        return send_file(report_path, as_attachment=True)  # Send as download
    return "PDF report not found.", 404  # Error if missing


# Route to download the Newick tree file
@app.route("/download_tree")
def download_tree():
    folder = session.get("custom_folder")  # Get result folder from session
    if not folder:
        return "No storage folder specified.", 400  # Error if not set

    tree_path = os.path.join(app.config["RESULT_FOLDER"], folder, "phylo_tree.nwk")  # Path to Newick tree
    if os.path.exists(tree_path):
        return send_file(tree_path, as_attachment=True)  # Download the .nwk tree file
    return "Newick file not found.", 404  # File not found error


#######################################################################################################################################################################################################################################################

############################################################################################### Status query for jobs (polling) + Application start ###################################################################################################

# Route to check the status of a background job (used for polling)
@app.route('/status/<job_id>')  # <job_id> is passed via the URL
def get_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)  # Try to fetch the job from Redis using the ID
        return jsonify({'status': job.get_status()})     # Return current job status (e.g., queued, started, finished)
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500  # If failed, return error with message
    
@app.route("/cancel_jobs", methods=["POST"])
def cancel_jobs():
    try:
        job_ids = request.json.get("job_ids", [])
        cancelled = []
        for job_id in job_ids:
            job = Job.fetch(job_id, connection=redis_conn)
            if job.get_status() not in ("finished", "failed"):
                job.cancel()
                cancelled.append(job_id)
        return jsonify({"status": "cancelled", "jobs": cancelled})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



# Only runs the Flask development server if this file is run directly (not imported as module)
if __name__ == '__main__':
    app.run(debug=True)  

##########################################################################################################################################################################################################################################################