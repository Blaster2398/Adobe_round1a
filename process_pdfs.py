import fitz  # PyMuPDF
import os
import json
import sys
import re
import unicodedata
from pathlib import Path
from collections import Counter
from statistics import median

# Define input and output directories as per Docker requirements
INPUT_DIR = Path("/app/input")
OUTPUT_DIR = Path("/app/output")

def extract_text_details(pdf_path):
    """
    Extracts text information from a PDF, filtering noise and capturing layout details.
    """
    document_lines = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            blocks = page.get_text("dict")["blocks"]
            page_height = page.mediabox.height
            page_width = page.mediabox.width
            current_page_lines = []
            prev_y1 = None

            for block in blocks:
                if block["type"] != 0:  # Skip non-text blocks
                    continue
                for line in block["lines"]:
                    line_text = ""
                    line_spans_details = []
                    min_x0 = float('inf')
                    max_x1 = float('-inf')
                    min_y0 = float('inf')
                    max_y1 = float('-inf')

                    for span in line["spans"]:
                        text = span["text"].strip()
                        if not text:
                            continue
                        text = unicodedata.normalize("NFKC", text)
                        # Skip separators or non-semantic text
                        if re.match(r'^[-=~|*#+]{2,}$', text) or len(text) < 2:
                            continue
                        line_text += text + " "
                        line_spans_details.append({
                            "text": text,
                            "font": span["font"],
                            "size": round(span["size"], 2),
                            "flags": span["flags"],
                            "bbox": span["bbox"]
                        })
                        min_x0 = min(min_x0, span["bbox"][0])
                        max_x1 = max(max_x1, span["bbox"][2])
                        min_y0 = min(min_y0, span["bbox"][1])
                        max_y1 = max(max_y1, span["bbox"][3])

                    line_text = line_text.strip()
                    if not line_text or len(line_text) < 3 or sum(c.isalnum() for c in line_text) < 2:
                        continue
                    # Filter headers/footers
                    if min_y0 < 0.1 * page_height or max_y1 > 0.9 * page_height:
                        continue

                    spacing_above = (min_y0 - prev_y1) if prev_y1 is not None else 0
                    prev_y1 = max_y1

                    current_page_lines.append({
                        "text": line_text,
                        "page": page_num + 1,
                        "bbox": (min_x0, min_y0, max_x1, max_y1),
                        "spans": line_spans_details,
                        "is_centered": abs(min_x0 + max_x1 - page_width) / page_width < 0.25,
                        "spacing_above": spacing_above,
                        "block_density": len(block["lines"])  # Indicates if part of dense text block
                    })
            document_lines.extend(current_page_lines)
        doc.close()
        return document_lines
    except Exception as e:
        print(f"Error processing {pdf_path} during text extraction: {e}", file=sys.stderr)
        return []

def is_bold(flags):
    """Checks if the font flags indicate bold text."""
    return (flags & 4) != 0

def is_heading_numbered(text):
    """Checks if text starts with a numbering pattern (e.g., '1.', '1.1')."""
    return bool(re.match(r'^\d+(\.\d+)*(\.\s|\s|$)', text))

def compute_heading_score(line, heading_size_map, body_text_size):
    """Computes a score to determine if a line is a heading."""
    avg_size = sum(span["size"] for span in line["spans"]) / len(line["spans"]) if line["spans"] else 0
    is_any_bold = any(is_bold(span["flags"]) for span in line["spans"])
    is_numbered = is_heading_numbered(line["text"])
    is_short = len(line["text"]) < 80
    is_centered = line["is_centered"]
    spacing_above = line["spacing_above"] if line["spacing_above"] > 0 else 0
    is_sparse = line["block_density"] <= 3  # Headings often in small blocks

    score = 0
    if avg_size > body_text_size * 1.2:
        score += 40
    if is_any_bold:
        score += 25
    if is_numbered:
        score += 25
    if is_short:
        score += 20
    if is_centered:
        score += 15
    if spacing_above > avg_size * 2:
        score += 20
    if is_sparse:
        score += 15

    # Bonus for matching heading sizes
    if "H1" in heading_size_map and avg_size >= heading_size_map["H1"] * 0.95:
        score += 25
    elif "H2" in heading_size_map and avg_size >= heading_size_map["H2"] * 0.95:
        score += 20
    elif "H3" in heading_size_map and avg_size >= heading_size_map["H3"] * 0.95:
        score += 15

    return score

def identify_headings(lines, pdf_path):
    """
    Identifies title, H1, H2, and H3 headings using refined heuristics.
    """
    if not lines:
        return {"title": "No Title Found", "outline": []}

    # Get metadata title
    title = "No Title Found"
    try:
        doc = fitz.open(pdf_path)
        metadata = doc.metadata
        if metadata.get("title") and metadata["title"].strip() and sum(c.isalnum() for c in metadata["title"]) >= 3:
            title = unicodedata.normalize("NFKC", metadata["title"].strip())
        doc.close()
    except Exception:
        pass

    # Determine body text font size
    all_font_sizes = [span["size"] for line in lines for span in line["spans"] if span["size"] > 6]
    if not all_font_sizes:
        return {"title": title, "outline": []}

    body_text_size = median(all_font_sizes)  # Use median for robustness
    size_counts = Counter([round(s, 1) for s in all_font_sizes]).most_common()
    if size_counts:
        body_text_size = max(body_text_size, size_counts[0][0])  # Prefer most common if close

    # Identify heading sizes
    potential_heading_sizes = sorted(
        list(set([s for s in all_font_sizes if s > body_text_size * 1.2])),
        reverse=True
    )

    heading_size_map = {}
    if potential_heading_sizes:
        heading_size_map["H1"] = potential_heading_sizes[0]
    if len(potential_heading_sizes) >= 2 and potential_heading_sizes[1] < potential_heading_sizes[0] * 0.95:
        heading_size_map["H2"] = potential_heading_sizes[1]
    if len(potential_heading_sizes) >= 3 and potential_heading_sizes[2] < potential_heading_sizes[0] * 0.95:
        heading_size_map["H3"] = potential_heading_sizes[2]
    if len(potential_heading_sizes) >= 4 and potential_heading_sizes[3] < potential_heading_sizes[0] * 0.95:
        heading_size_map["H4"] = potential_heading_sizes[3]


    # Title detection
    first_page_lines = sorted(
        [line for line in lines if line["page"] == 1],
        key=lambda x: x["bbox"][1]
    )
    title_candidates = []
    current_title = []
    prev_size = None
    prev_y1 = None

    for line in first_page_lines:
        avg_size = sum(span["size"] for span in line["spans"]) / len(line["spans"]) if line["spans"] else 0
        if prev_size is None or (
            prev_y1 is not None and
            line["bbox"][1] - prev_y1 < avg_size * 1.5 and
            abs(avg_size - prev_size) < 1.0
        ):
            current_title.append(line)
        else:
            if current_title:
                title_candidates.append(current_title)
            current_title = [line]
        prev_size = avg_size
        prev_y1 = line["bbox"][3]
    if current_title:
        title_candidates.append(current_title)

    best_title_score = 0
    best_title_text = title
    for candidate in title_candidates:
        text = " ".join(line["text"] for line in candidate)
        if sum(c.isalnum() for c in text) < 3 or len(text) < 5:
            continue
        avg_size = sum(
            sum(span["size"] for span in line["spans"]) / len(line["spans"])
            for line in candidate
        ) / len(candidate)
        score = 0
        if avg_size > body_text_size * 1.3:
            score += 40
        if any(line["is_centered"] for line in candidate):
            score += 25
        if any(any(is_bold(span["flags"]) for span in line["spans"]) for line in candidate):
            score += 25
        if candidate[0]["bbox"][1] < 0.25 * fitz.open(pdf_path).load_page(0).mediabox.height:
            score += 30
        if len(candidate) == 1 or (len(candidate) > 1 and all(line["block_density"] <= 3 for line in candidate)):
            score += 20
        if score > best_title_score and score >= 80:
            best_title_score = score
            best_title_text = text

    if best_title_score >= 80:
        title = best_title_text

    # Identify headings
    outline = []
    seen_headings = set()
    headings_per_page = Counter()

    for line in lines:
        text = line["text"]
        page = line["page"]
        if sum(c.isalnum() for c in text) < 2 or len(text) < 3:
            continue
        if headings_per_page[page] > 8:  # Limit headings per page
            continue
        if line["block_density"] > 5:  # Skip dense text blocks
            continue

        score = compute_heading_score(line, heading_size_map, body_text_size)
        if score < 80:  # Strict threshold
            continue

        avg_size = sum(span["size"] for span in line["spans"]) / len(line["spans"]) if line["spans"] else 0
        level = None
        if (
            "H1" in heading_size_map and
            avg_size >= heading_size_map["H1"] * 0.95 and
            score >= 100
        ):
            level = "H1"
        elif (
            "H2" in heading_size_map and
            avg_size >= heading_size_map["H2"] * 0.95 and
            avg_size < (heading_size_map.get("H1", float('inf')) * 0.95) and
            score >= 90
        ):
            level = "H2"
        elif (
            "H3" in heading_size_map and
            avg_size >= heading_size_map["H3"] * 0.95 and
            avg_size < (heading_size_map.get("H2", float('inf')) * 0.95) and
            score >= 80
        ):
            level = "H3"

        if level and text != title:  # Avoid duplicating title
            heading_identifier = (text.lower().strip(), page, level)
            if heading_identifier not in seen_headings:
                outline.append({"level": level, "text": text, "page": page, "y0": line["bbox"][1]})
                seen_headings.add(heading_identifier)
                headings_per_page[page] += 1

    # Sort by page and y-position
    outline.sort(key=lambda x: (x["page"], x["y0"]))
    for entry in outline:
        del entry["y0"]

    # Fallback: Use first H1 as title if no title found
    if title == "No Title Found" and outline:
        for entry in outline:
            if entry["level"] == "H1":
                title = entry["text"]
                outline = [e for e in outline if not (e["text"] == title and e["page"] == entry["page"])]
                break

    return {"title": title, "outline": outline}

def process_pdfs():
    """Processes all PDFs in the input directory and generates JSON outlines."""
    input_dir = INPUT_DIR
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in '{input_dir}'.", file=sys.stderr)
        sys.exit(0)

    for pdf_file in pdf_files:
        print(f"Processing {pdf_file.name}...")
        lines = extract_text_details(pdf_file)
        if not lines:
            print(f"Skipping {pdf_file.name} due to extraction error.", file=sys.stderr)
            continue

        structured_output = identify_headings(lines, pdf_file)
        output_file = output_dir / f"{pdf_file.stem}.json"

        try:
            with open(output_file, "w", encoding='utf-8') as f:
                json.dump(structured_output, f, indent=2, ensure_ascii=False)
            print(f"Generated outline for {pdf_file.name} -> {output_file.name}")
        except Exception as e:
            print(f"Error saving JSON for {pdf_file.name}: {e}", file=sys.stderr)

if __name__ == "__main__":
    print("Starting PDF processing...")
    process_pdfs()
    print("Completed PDF processing.")

