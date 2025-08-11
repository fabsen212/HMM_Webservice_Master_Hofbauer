import os

class Config:
    SECRET_KEY = os.urandom(24)
    UPLOAD_FOLDER = 'uploads'
    RESULT_FOLDER = 'results'
    PROTEIN_FOLDER = 'database/proteins'
    REDIS_URL = "redis://localhost:6379/0"
    RQ_REDIS_URL = "redis://localhost:6379/0"
    RQ_DEFAULT_JOB_TIMEOUT = 6000
    ALLOWED_EXTENSIONS = {'hmm', 'fasta'}
