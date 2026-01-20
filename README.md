# Web-based HMM Search and Phylogenetic Analysis Tool for Plant Protein Families

## Overview

This repository contains the source code and documentation for a web-based bioinformatics application developed as part of a Master’s thesis in Bioinformatics.  
The project implements an automated workflow for the detection, analysis, and visualization of protein domains in plant protein families using Hidden Markov Models (HMMs).

The application enables users to perform HMM-based searches against plant protein databases, generate multiple sequence alignments, construct phylogenetic trees, and explore results interactively through a web interface.

---

## Key Features

- Upload of custom FASTA or HMM files  
- Support for domain searches via Pfam identifiers  
- Species-specific filtering of plant protein databases  
- Automated execution of:
  - HMMER searches
  - Multiple sequence alignments (MAFFT)
  - Phylogenetic tree reconstruction (FastTree)
- Asynchronous background processing using Redis workers  
- Interactive result visualization (tables, domain architectures, phylogenetic trees)  
- Export of results as CSV and PDF reports  
- Session-based user isolation to ensure data separation  

---

## Application Architecture

The system follows a modular, service-oriented architecture:

### Frontend
- HTML, CSS, and JavaScript  
- Asynchronous form handling and progress tracking  
- Interactive visualizations (e.g. phylogenetic trees)

### Backend
- Flask-based web server  
- Modular Python pipeline for bioinformatics analyses  
- Redis-based task queue for long-running jobs  

### Data Flow
1. User uploads input data or specifies a Pfam ID  
2. Backend validates input and initializes a session-specific workspace  
3. Analysis pipeline is executed as a single coordinated job  
4. Results are stored, filtered, and visualized  
5. User accesses results via the web interface  

---

## Installation and Setup

### Requirements

- Python ≥ 3.9  
- Redis server  
- Linux-based environment recommended  

### Required Bioinformatics Tools

The following tools must be installed and available in the system PATH:

- HMMER  
- MAFFT  
- FastTree  

### Python Dependencies

Install all required Python packages using:

```bash
pip install -r requirements.txt
sudo apt install requirements_apt.txt
```

Start the Webservie using:

```bash
./start_hmmsearchtool.sh
```

## Scientific Context
Protein domains are fundamental functional and evolutionary units of proteins.
Hidden Markov Models are widely used for sensitive detection of conserved protein domains across large sequence datasets.

This project aims to:
- Provide an accessible web-based interface for domain-based protein family analysis
- Combine established bioinformatics tools into a reproducible, automated workflow
- Facilitate comparative and evolutionary analyses of plant protein families

The application is designed to support both exploratory research and reproducible scientific workflows.

## Thesis Context
This repository accompanies a Master’s thesis in Bioinformatics and serves as both:
- A functional research tool
- A demonstrator of software engineering practices in computational biology

The implementation emphasizes reproducibility, modularity, and transparency of bioinformatics analyses.

## License
This project is provided for academic and research purposes. Please consult the thesis document for detailed methodological descriptions and usage context.

## Author
Fabian Hofbauer MSc. 
Email: fabianhofbauer212@gmail.com
