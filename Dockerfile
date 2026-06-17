FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first for better layer caching
COPY pyproject.toml README.md ./
COPY src/ src/
COPY data/ data/
COPY config/ config/

# Install the jarvis package and dependencies
RUN pip install --no-cache-dir -e ".[backend,search]"

# Copy application code
COPY app/ app/
COPY requirements.txt ./
COPY backend_main.py ./

# Create cache directory for SQLite persistence
RUN mkdir -p /app/cache

# Expose ports: Streamlit (8501) and FastAPI (8000)
EXPOSE 8501 8000

# Default: run Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true

CMD ["streamlit", "run", "app/Home.py"]
