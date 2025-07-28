# Dockerfile
# Use a lightweight base image for Python 3.10 on AMD64
FROM --platform=linux/amd64 python:3.10-slim-bookworm

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required by PyMuPDF (fitz)
RUN apt-get update && apt-get install -y \
    libharfbuzz-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the processing script
COPY process_pdfs.py .

# Create input and output directories
RUN mkdir -p input output

# Default command
CMD ["python", "process_pdfs.py"]
