"""
Simple file server for serving uploaded legal documents.
This allows the scraper to access files via HTTP URLs.
"""

import streamlit as st
from pathlib import Path
import mimetypes
import os

def serve_file(file_path: Path):
    """Serve a file through Streamlit."""
    if not file_path.exists():
        st.error(f"File not found: {file_path}")
        return
    
    # Get file info
    file_size = file_path.stat().st_size
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # Set headers for file download
    st.set_page_config(page_title=f"File: {file_path.name}")
    
    # Read and serve file content
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        # Determine content type
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        # Serve the file
        st.download_button(
            label=f"Download {file_path.name}",
            data=file_content,
            file_name=file_path.name,
            mime=mime_type
        )
        
        # Also display content if it's text-based
        if mime_type.startswith('text/'):
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            st.text_area("File Content:", text_content, height=400)
            
    except Exception as e:
        st.error(f"Error reading file: {e}")

# Main file server logic
def main():
    st.title("📄 File Server")
    
    # Get file path from query parameters
    query_params = st.query_params
    file_name = query_params.get("file", "")
    
    if file_name:
        file_path = Path("hosted_files") / file_name
        serve_file(file_path)
    else:
        st.info("No file specified. Use: ?file=filename.html")

if __name__ == "__main__":
    main()
