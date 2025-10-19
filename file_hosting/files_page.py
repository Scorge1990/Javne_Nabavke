import streamlit as st
import os
from pathlib import Path
import json

# Set page configuration
st.set_page_config(
    page_title="LegaBot - Legal Documents",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Legal Documents Repository")
st.markdown("---")

# Create a directory for hosting files
FILES_DIR = Path("hosted_files")
FILES_DIR.mkdir(exist_ok=True)

# Sidebar for file management
with st.sidebar:
    st.subheader("📁 File Management")
    
    # File upload section
    st.subheader("📤 Upload Files")
    uploaded_files = st.file_uploader(
        "Upload legal documents (HTML, TXT, JSON)",
        type=['html', 'txt', 'json'],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        for uploaded_file in uploaded_files:
            # Save uploaded file
            file_path = FILES_DIR / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success(f"✅ Uploaded: {uploaded_file.name}")
    
    # File deletion section
    st.subheader("🗑️ Delete Files")
    existing_files = list(FILES_DIR.glob("*"))
    if existing_files:
        for file_path in existing_files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(file_path.name)
            with col2:
                if st.button("🗑️", key=f"delete_{file_path.name}"):
                    file_path.unlink()
                    st.rerun()

# Main content area
st.subheader("📋 Available Documents")

# Display all files in the hosted_files directory
existing_files = list(FILES_DIR.glob("*"))
if existing_files:
    for file_path in existing_files:
        with st.expander(f"📄 {file_path.name}"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Show file info
                file_size = file_path.stat().st_size
                st.write(f"**Size:** {file_size:,} bytes")
                st.write(f"**Type:** {file_path.suffix}")
                
                # Show file content preview
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Truncate content for preview
                    preview = content[:500] + "..." if len(content) > 500 else content
                    st.text_area("Content Preview:", preview, height=200, disabled=True)
                    
                except Exception as e:
                    st.error(f"Error reading file: {e}")
            
            with col2:
                # Download button
                with open(file_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download",
                        data=f.read(),
                        file_name=file_path.name,
                        mime="text/plain"
                    )
                
                # Copy URL button
                file_url = f"http://localhost:8501/files/{file_path.name}"
                st.code(file_url)
                st.button("📋 Copy URL", key=f"copy_{file_path.name}")
                
                # Show scraper command
                st.subheader("🕷️ Scraper Command")
                scraper_cmd = f"python scraper/scraper.py --url \"{file_url}\" --output-dir scraper/laws"
                st.code(scraper_cmd, language="bash")
else:
    st.info("📁 No files uploaded yet. Use the sidebar to upload legal documents.")

# Instructions section
st.markdown("---")
st.subheader("📖 How to Use")

st.markdown("""
### For Scraping Your Files:

1. **Upload your legal documents** using the sidebar
2. **Copy the file URL** from each document's section
3. **Run the scraper** using the provided command

### Example Scraper Commands:

```bash
# Scrape a single file
python scraper/scraper.py --url "http://localhost:8501/files/your_document.html" --output-dir scraper/laws

# Scrape multiple files (create a urls.txt file first)
python scraper/scraper.py --file scraper/urls.txt --output-dir scraper/laws
```

### Supported File Types:
- **HTML files** - Legal documents in HTML format
- **TXT files** - Plain text legal documents  
- **JSON files** - Structured legal data

### Tips:
- Make sure your Streamlit app is running on `localhost:8501`
- The scraper will extract law articles from HTML files
- JSON files will be processed as-is
- TXT files will be treated as plain text content
""")

# Footer
st.markdown("---")
st.markdown("🔗 **LegaBot Legal Documents Repository** | Built with Streamlit")
