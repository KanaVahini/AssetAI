import os
import sys
sys.path.append(os.path.dirname(__file__))

from pdf_extractor import process_pdf
from csv_extractor import process_tabular
from ocr_extractor import process_image
from email_extractor import process_email

def route_file(file_path):
    """
    Routes any file to the correct extractor.
    Works for any file from any plant.
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == ".pdf":
        return process_pdf(file_path)
    
    elif ext in [".csv", ".xlsx", ".xls"]:
        return process_tabular(file_path)
    
    elif ext in [".jpg", ".jpeg", ".png", ".tiff", ".bmp"]:
        return process_image(file_path)
    
    elif ext in [".txt", ".eml", ".msg"]:
        return process_email(file_path)
    
    else:
        print(f"  Unsupported file type: {ext}")
        return None