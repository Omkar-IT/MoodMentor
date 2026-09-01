FROM python:3.10-slim

WORKDIR /app

# Install system packages required for PostgreSQL and compiling dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download spaCy sentence model
RUN python -m spacy download xx_sent_ud_sm

# Copy all project code into the container
COPY . .

# Run Streamlit directly on Render's assigned port
CMD streamlit run app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true --server.enableCORS false --server.enableXsrfProtection false