import fitz  # PyMuPDF
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
import unicodedata
from src.round_1a import process_pdfs

def get_keywords(text):
    """Extract keywords using NLTK tokenization."""
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words("english"))
    keywords = [t for t in tokens if t.isalnum() and t not in stop_words]
    return list(set(keywords))

def extract_section_text(doc, heading, outline):
    """Extract text from a heading to the next heading or page end."""
    page_num = heading["page"] - 1
    page = doc.load_page(page_num)
    blocks = page.get_text("dict")["blocks"]
    section_text = []
    start_y = heading.get("y0", 0)

    # Find next heading
    next_heading_y = float("inf")
    for h in outline:
        if h["page"] > heading["page"]:
            next_heading_y = 0
            break
        if h["page"] == heading["page"] and h["text"] != heading["text"] and h.get("y0", 0) > start_y:
            next_heading_y = h["y0"]
            break

    for block in blocks:
        if block["type"] != 0:
            continue
        for line in block["lines"]:
            y0 = line["bbox"][1]
            if start_y <= y0 < next_heading_y:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        section_text.append(unicodedata.normalize("NFKC", text))

    return " ".join(section_text)

def run_round_1a(pdf_file, output_dir):
    """Run Round 1A outline extraction for a single PDF."""
    from src.round_1a import extract_text_details, identify_headings
    lines = extract_text_details(pdf_file)
    if lines:
        structured_output = identify_headings(lines, pdf_file)
        output_file = output_dir / f"{pdf_file.stem}.json"
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(structured_output, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving {output_file}: {e}", file=sys.stderr)
9
