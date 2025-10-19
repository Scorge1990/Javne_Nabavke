# PowerShell script to start both LegaBot servers

Write-Host "Starting LegaBot servers..." -ForegroundColor Green
Write-Host ""

# Start file server
Write-Host "Starting file server on port 8080..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python simple_file_server.py"

# Wait a moment
Start-Sleep -Seconds 3

# Start Streamlit app
Write-Host "Starting Streamlit app on port 8501..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\.venv\Scripts\python.exe -m streamlit run app.py"

Write-Host ""
Write-Host "Both servers are starting..." -ForegroundColor Green
Write-Host "File Server: http://localhost:8080" -ForegroundColor Cyan
Write-Host "Streamlit App: http://localhost:8501" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
