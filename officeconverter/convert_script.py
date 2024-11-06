import subprocess
from pathlib import Path

def convert_doc_to_docx(doc_path, docx_path):
    doc_path = Path(doc_path)
    
    cmd = [
        'libreoffice', 
        '--convert-to', 'docx',
        '--headless', 
        str(doc_path)
    ]
    
    subprocess.run(cmd, check=True)
    return docx_path

# Example usage
if __name__ == "__main__":
    doc_path = 'path/to/your/document.doc'
    docx_path = 'path/to/your/document.docx'
    docx_path = convert_doc_to_docx(doc_path, docx_path)
    print(f"Converted to {docx_path}")
