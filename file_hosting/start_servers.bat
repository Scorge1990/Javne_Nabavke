@echo off
echo Starting LegaBot servers...
echo.

echo Starting file server on port 8080...
start "File Server" cmd /k "python simple_file_server.py"

timeout /t 3 /nobreak >nul

echo Starting Streamlit app on port 8501...
start "Streamlit App" cmd /k ".\.venv\Scripts\python.exe -m streamlit run app.py"

echo.
echo Both servers are starting...
echo File Server: http://localhost:8080
echo Streamlit App: http://localhost:8501
echo.
echo Press any key to exit...
pause >nul
