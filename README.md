# Connecting the Dots Challenge: Round 1B

## Overview
This repository contains the solution for Round 1B of the Adobe India Hackathon "Connecting the Dots" Challenge. The system processes a collection of up to 10 multi-page PDFs, extracts 5 relevant sections and subsections based on a persona and job-to-be-done (JTBD), and generates `challenge1b_output.json` for each collection. It reuses Round 1A’s outline extraction, uses NLTK for tokenization, and TF-IDF for relevance scoring.

## Approach
- **Input**: Read `challenge1b_input.json` and PDFs from `Collection X/pdfs/`.
- **Outline Extraction**: Use `round_1a.py` to generate heading outlines.
- **Keyword Extraction**: Tokenize persona and JTBD with NLTK, removing stopwords.
- **Section Extraction**: Extract section text with PyMuPDF.
- **TF-IDF Scoring**: Score sections using `sklearn.TfidfVectorizer`, cache vectors, and select top 5 sections.
- **Subsection Analysis**: Refine subsection text (~150–200 words) based on TF-IDF scores.
- **Output**: Generate `challenge1b_output.json` with metadata, 5 sections, and 5 subsections.

See `approach_explanation.md` for details.

## Dependencies
- Python 3.9
- PyMuPDF==1.23.26
- NLTK==3.8.1
- scikit-learn==1.4.2

## Directory Structure