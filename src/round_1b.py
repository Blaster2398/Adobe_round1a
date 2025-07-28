import json
import sys
from datetime import datetime
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
import nltk
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
import fitz  # PyMuPDF
from src.utils import extract_section_text, get_keywords, run_round_1a

# Download NLTK data (pre-installed in Docker)
nltk.data.path.append("/app/nltk_data")

# Directories
INPUT_DIR = Path("/app/input")
OUTPUT_DIR = Path("/app/output")

def process_collection(collection_dir):
    """Process a single collection, generating challenge1b_output.json."""
    input_json = collection_dir / "challenge1b_input.json"
    pdfs_dir = collection_dir / "pdfs"
    output_collection_dir = OUTPUT_DIR / collection_dir.name
    output_collection_dir.mkdir(parents=True, exist_ok=True)

    # Read input JSON
    try:
        with open(input_json, "r", encoding="utf-8") as f:
            input_data = json.load(f)
    except Exception as e:
        print(f"Error reading {input_json}: {e}", file=sys.stderr)
        return

    persona = input_data["persona"]["role"]
    jtbd = input_data["job_to_be_done"]["task"]
    documents = [doc["filename"] for doc in input_data["documents"]]

    # Run Round 1A for outlines
    outlines = {}
    for pdf_file in pdfs_dir.glob("*.pdf"):
        if pdf_file.name in documents:
            outline_json = output_collection_dir / f"{pdf_file.stem}.json"
            if not outline_json.exists():
                run_round_1a(pdf_file, output_collection_dir)
            try:
                with open(outline_json, "r", encoding="utf-8") as f:
                    outlines[pdf_file.name] = json.load(f)
            except Exception as e:
                print(f"Error loading {outline_json}: {e}", file=sys.stderr)
                continue

    # Extract keywords
    keywords = get_keywords(persona + " " + jtbd)

    # Extract sections and text
    sections = []
    for doc_name, outline_data in outlines.items():
        doc_path = pdfs_dir / doc_name
        try:
            doc = fitz.open(doc_path)
            for heading in outline_data["outline"]:
                section_text = extract_section_text(doc, heading, outlines[doc_name]["outline"])
                sections.append({
                    "document": doc_name,
                    "title": heading["text"],
                    "page": heading["page"],
                    "text": section_text,
                    "level": heading["level"]
                })
            doc.close()
        except Exception as e:
            print(f"Error processing {doc_name}: {e}", file=sys.stderr)

    # TF-IDF scoring
    tfidf_vectorizer = TfidfVectorizer()
    section_texts = [s["title"] + " " + s["text"] for s in sections]
    tfidf_matrix = tfidf_vectorizer.fit_transform(section_texts)
    feature_names = tfidf_vectorizer.get_feature_names_out()
    keyword_scores = {}
    for keyword in keywords:
        if keyword in feature_names:
            keyword_scores[keyword] = tfidf_matrix[:, feature_names.tolist().index(keyword)].toarray()

    # Rank sections
    ranked_sections = []
    for i, section in enumerate(sections):
        score = 0
        for keyword in keywords:
            if keyword in keyword_scores:
                title_score = 2.0 * sum(keyword in section["title"].lower() for keyword in keyword_scores) / len(keyword_scores)
                content_score = sum(keyword_scores[keyword][i][0] for keyword in keyword_scores) / len(keyword_scores)
                score += title_score + content_score
        level_weight = {"H1": 1.0, "H2": 0.8, "H3": 0.6}.get(section["level"], 0.6)
        score *= level_weight
        ranked_sections.append({"section": section, "score": score})

    ranked_sections.sort(key=lambda x: x["score"], reverse=True)
    top_sections = [
        {
            "document": s["section"]["document"],
            "section_title": s["section"]["title"],
            "page_number": s["section"]["page"],
            "importance_rank": i + 1
        }
        for i, s in enumerate(ranked_sections[:5])
    ]

    # Subsection analysis
    subsection_analysis = []
    for i, top_section in enumerate(top_sections):
        doc_name = top_section["document"]
        section_title = top_section["section_title"]
        page_number = top_section["page_number"]
        outline = outlines[doc_name]["outline"]
        section_idx = next(
            (j for j, h in enumerate(outline) if h["text"] == section_title and h["page"] == page_number),
            -1
        )
        if section_idx == -1:
            continue

        # Find subsections
        subsections = []
        current_level = outline[section_idx]["level"]
        for j in range(section_idx + 1, len(outline)):
            if outline[j]["level"] in ["H1", "H2"] and current_level == "H1":
                break
            if outline[j]["level"] == "H1" and current_level == "H2":
                break
            subsections.append(outline[j])

        doc = fitz.open(pdfs_dir / doc_name)
        for subsection in subsections[:1]:  # Limit to one subsection per section for simplicity
            subsection_text = extract_section_text(doc, subsection, outline)
            sentences = sent_tokenize(subsection_text)
            sentence_scores = []
            for sentence in sentences:
                score = sum(keyword_scores.get(keyword, [0])[0] for keyword in keywords if keyword in sentence.lower())
                sentence_scores.append((sentence, score))
            sentence_scores.sort(key=lambda x: x[1], reverse=True)
            refined_text = " ".join(s[0] for s in sentence_scores[:5] if s[1] > 0)[:1000]  # ~150-200 words
            if refined_text:
                subsection_analysis.append({
                    "document": doc_name,
                    "refined_text": refined_text[:200],
                    "page_number": subsection["page"],
                    "importance_rank": i + 1
                })
        doc.close()

    # Generate output
    output_data = {
        "metadata": {
            "input_documents": documents,
            "persona": persona,
            "job_to_be_done": jtbd,
            "processing_timestamp": datetime.utcnow().isoformat() + "Z"
        },
        "extracted_sections": top_sections,
        "subsection_analysis": subsection_analysis[:5]
    }

    output_file = output_collection_dir / "challenge1b_output.json"
    try:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"Generated {output_file}")
    except Exception as e:
        print(f"Error saving {output_file}: {e}", file=sys.stderr)

def main():
    """Process all collections in the input directory."""
    print("Starting Round 1B processing...")
    for collection_dir in INPUT_DIR.iterdir():
        if collection_dir.is_dir() and collection_dir.name.startswith("Collection"):
            print(f"Processing {collection_dir.name}...")
            process_collection(collection_dir)
    print("Completed Round 1B processing.")

if __name__ == "__main__":
    main()