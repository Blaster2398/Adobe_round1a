# Use AMD64-compatible base image
FROM --platform=linux/amd64 python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libmupdf-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download NLTK data
RUN python -m nltk.downloader -d /app/nltk_data punkt stopwords

# Copy source code
COPY src/ src/

# Set NLTK data path
ENV NLTK_DATA=/app/nltk_data

# Run Round 1B script
CMD ["python", "src/round_1b.py"]