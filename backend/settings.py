"""Настройки проекта."""
from dotenv import load_dotenv
import os


load_dotenv()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", default="./upload_dir")
RESULTS_DIR = os.getenv("RESULTS_DIR", default="./results_dir")