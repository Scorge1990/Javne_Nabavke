"""
Simple HTTP file server for serving legal documents to the scraper.
Run this alongside your Streamlit app to serve files via HTTP.
"""

import http.server
import socketserver
import os
from pathlib import Path
import webbrowser
import threading
import time

# Configuration
HOST = "localhost"
PORT = 8080
FILES_DIR = Path("hosted_files")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from hosted_files directory."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FILES_DIR), **kwargs)
    
    def end_headers(self):
        # Add CORS headers to allow cross-origin requests
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        # Ensure the files directory exists
        FILES_DIR.mkdir(exist_ok=True)
        
        # If requesting root, show file list
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Generate HTML file list
            html = self.generate_file_list_html()
            self.wfile.write(html.encode())
        else:
            # Serve the requested file
            super().do_GET()
    
    def generate_file_list_html(self):
        """Generate HTML page showing available files."""
        files = list(FILES_DIR.glob("*"))
        
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>LegaBot File Server</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .file-list { list-style: none; padding: 0; }
                .file-item { 
                    background: #f5f5f5; 
                    margin: 10px 0; 
                    padding: 15px; 
                    border-radius: 5px;
                    border-left: 4px solid #FF6B6B;
                }
                .file-name { font-weight: bold; color: #333; }
                .file-url { color: #666; font-size: 0.9em; }
                .scraper-cmd { 
                    background: #f0f0f0; 
                    padding: 10px; 
                    border-radius: 3px; 
                    font-family: monospace;
                    margin-top: 10px;
                }
                h1 { color: #FF6B6B; }
            </style>
        </head>
        <body>
            <h1>📄 LegaBot File Server</h1>
            <p>Available legal documents for scraping:</p>
        """
        
        if files:
            html += "<ul class='file-list'>"
            for file_path in files:
                file_url = f"http://{HOST}:{PORT}/{file_path.name}"
                scraper_cmd = f"python scraper/scraper.py --url \"{file_url}\" --output-dir scraper/laws"
                
                html += f"""
                <li class='file-item'>
                    <div class='file-name'>📄 {file_path.name}</div>
                    <div class='file-url'>URL: <a href='{file_url}' target='_blank'>{file_url}</a></div>
                    <div class='scraper-cmd'>Scraper Command:<br>{scraper_cmd}</div>
                </li>
                """
            html += "</ul>"
        else:
            html += "<p>No files available. Upload files to the hosted_files directory.</p>"
        
        html += """
            <hr>
            <h2>📖 How to Use:</h2>
            <ol>
                <li>Upload your legal documents to the <code>hosted_files</code> directory</li>
                <li>Copy the file URL from above</li>
                <li>Run the scraper command in your terminal</li>
            </ol>
            
            <h2>🕷️ Batch Scraping:</h2>
            <p>To scrape multiple files, create a <code>urls.txt</code> file with one URL per line:</p>
            <pre>
http://localhost:8080/file1.html
http://localhost:8080/file2.html
http://localhost:8080/file3.html
            </pre>
            <p>Then run: <code>python scraper/scraper.py --file urls.txt --output-dir scraper/laws</code></p>
        </body>
        </html>
        """
        
        return html

def start_server():
    """Start the HTTP file server."""
    # Ensure the files directory exists
    FILES_DIR.mkdir(exist_ok=True)
    
    try:
        with socketserver.TCPServer((HOST, PORT), CustomHTTPRequestHandler) as httpd:
            print(f"🚀 File server started at http://{HOST}:{PORT}")
            print(f"📁 Serving files from: {FILES_DIR.absolute()}")
            print("📄 Open http://localhost:8080 in your browser to see available files")
            print("🛑 Press Ctrl+C to stop the server")
            
            # Open browser automatically
            threading.Timer(1.0, lambda: webbrowser.open(f"http://{HOST}:{PORT}")).start()
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except OSError as e:
        if e.errno == 10048:  # Port already in use
            print(f"❌ Port {PORT} is already in use. Please stop other servers or change the port.")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    start_server()
