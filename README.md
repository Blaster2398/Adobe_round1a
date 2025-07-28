# PDF Outline Extractor

This project extracts titles and structured outlines (H1, H2, H3) from PDF documents using `PyMuPDF` and layout-based heuristics. It can run locally with Python or inside a Docker container.

-----

## 📁 Project Structure

```
Challenge_1b/
├── Dockerfile              # Docker setup using Python 3.10-slim
├── requirements.txt        # Contains PyMuPDF dependency
├── process_pdfs.py         # Main PDF processing script
├── input/                  # Place PDFs here
└── output/                 # JSON output goes here
```

-----

## 🚀 Local Python Setup

Follow these steps to set up and run the script locally using Python:

1.  **Create a virtual environment:**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use: .\venv\Scripts\activate
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the script:**

    ```bash
    python process_pdfs.py
    ```

-----

## 🐳 Docker Usage

Use these commands to build and run the project with Docker:

### 1️⃣ Build the Docker Image

```bash
docker build --platform linux/amd64 -t pdf-processor:v1 .
```

### 2️⃣ Run the Container (Windows Path Example)

```bash
docker run --rm ^
  --mount type=bind,source="C:/Users/aryan/Desktop/ADOBE/New/input",target=/app/input,readonly ^
  --mount type=bind,source="C:/Users/aryan/Desktop/ADOBE/New/output",target=/app/output ^
  --network none ^
  pdf-processor:v1
```

> 💡 **Adjust Paths:** Make sure to adjust the `source` paths for your `input` and `output` directories if they are different from the example. For Linux/macOS, replace `^` with `\` for line continuation.

### 3️⃣ Remove the Docker Image

```bash
docker rmi pdf-processor:v1
```

-----

## 📤 Output Format

Each processed `.pdf` file will generate a corresponding `.json` file in the `output/` directory with the following structure:

```json
{
  "title": "Document Title",
  "outline": [
    { "level": "H1", "text": "1. Introduction", "page": 1 },
    { "level": "H2", "text": "1.1 Background", "page": 2 }
  ]
}
```

-----

## 🔧 Requirements

  * **Python:** 3.9+ (for local use)
  * **Docker:** (for containerized use)
  * **Library:** `PyMuPDF==1.24.5`

-----

## 🧹 Cleanup

  * **Exit virtual environment:**
    ```bash
    deactivate
    ```
  * **Remove Docker image:**
    ```bash
    docker rmi pdf-processor:v1
    ```
  * **Remove stopped Docker containers:**
    ```bash
    docker container prune
    ```
