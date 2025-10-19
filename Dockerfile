FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p .streamlit

# Create streamlit config
RUN echo "[server]\nheadless = true\nport = 8501\nenableCORS = false\n" > .streamlit/config.toml

# Expose port
EXPOSE 8501

# Run the app
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
