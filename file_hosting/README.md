# 📄 File Hosting for LegaBot Scraper

This folder contains all the tools needed to host your legal documents so the scraper can access and process them.

## 📁 Files in this folder:

- **`files_page.py`** - Streamlit page for uploading and managing legal documents
- **`simple_file_server.py`** - HTTP server to serve files for scraping
- **`file_server.py`** - Alternative file server implementation
- **`start_servers.bat`** - Windows batch script to start both servers
- **`start_servers.ps1`** - PowerShell script to start both servers

## 🚀 Quick Start:

### Option 1: Use the Batch Script (Windows)
```bash
# Double-click or run:
start_servers.bat
```

### Option 2: Use PowerShell Script
```powershell
# Run in PowerShell:
.\start_servers.ps1
```

### Option 3: Manual Setup
```bash
# Terminal 1 - Start file server
python simple_file_server.py

# Terminal 2 - Start Streamlit app
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## 📋 How to Use:

1. **Start the servers** using one of the methods above
2. **Upload your legal documents** to the `hosted_files` folder (created automatically)
3. **Access the file server** at `http://localhost:8080` to see available files
4. **Copy the file URLs** and use them with the scraper

## 🕷️ Scraping Your Files:

### Single File Scraping:
```bash
python scraper/scraper.py --url "http://localhost:8080/your_document.html" --output-dir scraper/laws
```

### Batch Scraping:
1. Create a `urls.txt` file with your file URLs:
```
http://localhost:8080/document1.html
http://localhost:8080/document2.html
http://localhost:8080/document3.html
```

2. Run the scraper:
```bash
python scraper/scraper.py --file urls.txt --output-dir scraper/laws
```

## 🌐 URLs:

- **File Server**: `http://localhost:8080` - View and access your hosted files
- **Streamlit App**: `http://localhost:8501` - Your main LegaBot application
- **File Management**: `http://localhost:8501` - Upload files via Streamlit interface

## 📝 Supported File Types:

- **HTML files** - Legal documents in HTML format (recommended for scraping)
- **TXT files** - Plain text legal documents
- **JSON files** - Structured legal data

## 🔧 Configuration:

- **File Server Port**: 8080 (change in `simple_file_server.py` if needed)
- **Streamlit Port**: 8501 (default Streamlit port)
- **Files Directory**: `hosted_files/` (created automatically)

## 💡 Tips:

- Make sure both servers are running before scraping
- HTML files work best with the scraper as they maintain structure
- The file server automatically creates the `hosted_files` directory
- You can upload files via the Streamlit interface or directly to the `hosted_files` folder
- The scraper will extract law articles from HTML files automatically

## 🛠️ Troubleshooting:

- **Port already in use**: Change the port in `simple_file_server.py`
- **Files not accessible**: Check that the `hosted_files` directory exists
- **Scraper errors**: Ensure the file server is running and accessible
- **Permission errors**: Run as administrator if needed on Windows
