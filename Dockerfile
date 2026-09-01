FROM python:3.10-slim

WORKDIR /app

# Install system packages required for PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download spaCy sentence model
RUN python -m spacy download xx_sent_ud_sm

# Copy all project code
COPY . .

# Run FastAPI in the background and Streamlit in the foreground bound to Render's $PORT
CMD uvicorn backend:app --host 0.0.0.0 --port 8000 & \
    streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false