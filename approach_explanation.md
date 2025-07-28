# Approach Explanation for Round 1B: Persona-Driven Document Intelligence

## Overview
This solution addresses Round 1B of the "Connecting the Dots" Challenge, extracting relevant sections and subsections from a collection of up to 10 multi-page PDFs based on a persona and job-to-be-done (JTBD) specified in `challenge1b_input.json`. The system reuses Round 1A’s outline extraction, employs NLTK for tokenization, and uses TF-IDF for relevance scoring, producing `challenge1b_output.json` with metadata, 5 sections, and 5 subsections. It adheres to constraints: CPU-only, ≤1GB model size, ≤60s processing time, and no internet access.

## Methodology
1. **Input Processing**:
   - Read `challenge1b_input.json` to extract the persona role (e.g., “Travel Planner”), JTBD (e.g., “Plan a 4-day trip”), and document list.
   - Load PDFs from the collection’s `pdfs` folder.

2. **Outline Extraction**:
   - Reuse Round 1A’s `round_1a.py` to generate outline JSONs for each PDF, containing the title and headings (H1, H2, H3) with page numbers.
   - Cache outlines in `/app/output/Collection X/` to avoid redundant processing.

3. **Keyword Extraction**:
   - Use NLTK’s `punkt` tokenizer and `stopwords` to extract keywords from the persona role and JTBD, normalizing text (lowercase, NFKC) to ensure consistency.
   - Example: For “Plan a 4-day trip for a group of 10 college friends,” keywords include “plan,” “trip,” “college,” “friends.”

4. **Section Extraction**:
   - Load Round 1A JSONs to identify headings and their page numbers.
   - Extract section text using PyMuPDF, from the heading’s y-position to the next heading or page end, handling multi-page PDFs.

5. **TF-IDF Scoring**:
   - Build a TF-IDF corpus from section titles and content using `sklearn.TfidfVectorizer`.
   - Cache TF-IDF vectors for efficiency.
   - Score sections based on TF-IDF matches for persona/JTBD keywords, with title matches weighted 2.0x, and heading levels weighted (H1: 1.0, H2: 0.8, H3: 0.6).
   - Select the top 5 sections by score.

6. **Subsection Analysis**:
   - For each top section, identify subsections (H2 under H1, H3 under H2) from the outline.
   - Extract subsection text, tokenize with NLTK, and select sentences with high TF-IDF scores, limiting to ~150–200 words.
   - Assign ranks matching section order (1–5).

7. **Output Generation**:
   - Produce `challenge1b_output.json` with metadata (documents, persona, JTBD, timestamp), 5 sections (document, title, page, rank), and 5 subsections (document, refined text, page, rank).
   - Save to `/app/output/Collection X/challenge1b_output.json`.

## Optimization
- **Performance**: Cache Round 1A outlines and TF-IDF vectors to meet the 60-second constraint for 3–10 PDFs.
- **Size**: Use lightweight libraries (PyMuPDF, NLTK, scikit-learn) within 1GB.
- **Offline**: Pre-download NLTK data (`punkt`, `stopwords`) in Docker.
- **Generality**: TF-IDF scoring ensures flexibility across domains (e.g., travel, academic, business).

## Libraries
- **PyMuPDF**: PDF text extraction.
- **NLTK**: Tokenization and stopword removal.
- **scikit-learn**: TF-IDF scoring.

This approach balances accuracy, efficiency, and generality, enabling persona-driven document analysis for diverse use cases like travel planning.

*Word Count: 346*