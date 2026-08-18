"""
=============================================================================
Multi-PDF Topic Extractor - Backend Server (Flask)
=============================================================================
This application allows users to upload up to 5 PDF files, enter a topic or
keyword, and extract the most relevant paragraphs from each PDF using
TF-IDF (Term Frequency - Inverse Document Frequency) Vectorization and
Cosine Similarity. If semantic matching finds no strong results, a case-
insensitive keyword fallback ensures high retrieval accuracy.

Key Components & Pipeline:
1. PDF Text Extraction (pdfplumber) - Extracts text with page-level tracking.
2. Text Cleaning & Chunking - Splits document into coherent paragraphs.
3. TF-IDF Vectorization & Cosine Similarity - Semantic relevance scoring.
4. Fallback Keyword Matching - Direct phrase/word matching if TF-IDF score is 0.
5. Search Term Highlighting - Wraps matched keywords in <mark> tags for UI.
=============================================================================
"""

import os
import re
import html
import tempfile
import logging
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import pdfplumber
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import nltk

# ---------------------------------------------------------------------------
# NLTK Setup (Download punkt if available, with graceful offline fallback)
# ---------------------------------------------------------------------------
try:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)
except Exception:
    pass

# ---------------------------------------------------------------------------
# Flask App Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024  # 32 MB upload limit
ALLOWED_EXTENSIONS = {'pdf'}
MAX_PDF_COUNT = 5
TOP_N_RESULTS = 3  # Number of top paragraphs to extract per PDF
SIMILARITY_THRESHOLD = 0.03  # Minimum cosine similarity threshold

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_allowed_file(filename: str) -> bool:
    """Check if the uploaded file has a .pdf extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------------------------------------------------------------------
# STEP 1: PDF Text Extraction (using pdfplumber)
# ---------------------------------------------------------------------------
def extract_text_from_pdf(pdf_path: str):
    """
    Extracts raw text from a PDF file page by page using pdfplumber.
    
    Returns:
        tuple: (list of page dicts with page_num & text, total_pages_count)
    """
    pages_data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            for page_index, page in enumerate(pdf.pages, start=1):
                raw_text = page.extract_text()
                if raw_text:
                    pages_data.append({
                        "page_number": page_index,
                        "text": raw_text
                    })
        return pages_data, total_pages
    except Exception as e:
        logging.error(f"Error reading PDF {pdf_path}: {e}")
        return [], 0


# ---------------------------------------------------------------------------
# STEP 2: Text Cleaning & Paragraph Segmentation
# ---------------------------------------------------------------------------
def segment_into_paragraphs(pages_data):
    """
    Cleans and segments page texts into coherent paragraphs/sections.
    Maintains the originating page number for each paragraph.
    If a section is overly long, chunks it into coherent multi-sentence blocks.
    
    Returns:
        list of dicts: [{"page": 1, "text": "cleaned paragraph content..."}]
    """
    paragraphs = []

    for page_info in pages_data:
        page_num = page_info["page_number"]
        page_text = page_info["text"]

        # Fix hyphenated words broken across line breaks (e.g. "photo-\nsynthesis" -> "photosynthesis")
        normalized_text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', page_text)
        
        # Normalize carriage returns
        normalized_text = normalized_text.replace('\r\n', '\n').replace('\r', '\n')

        # Split on double newlines or multiple blank lines to identify paragraphs
        raw_chunks = re.split(r'\n\s*\n+', normalized_text)

        for chunk in raw_chunks:
            # Replace single internal newlines with space to form a coherent text block
            cleaned = re.sub(r'\s+', ' ', chunk).strip()
            
            # Skip empty or trivial snippets
            if len(cleaned) < 25 or len(cleaned.split()) < 4:
                continue

            # If the chunk is very long (> 500 chars), group sentences into 2-3 sentence units
            if len(cleaned) > 500:
                try:
                    sentences = nltk.sent_tokenize(cleaned)
                except Exception:
                    sentences = re.split(r'(?<=[.!?])\s+', cleaned)

                if len(sentences) > 3:
                    # Group sentences in chunks of 2-3
                    for i in range(0, len(sentences), 2):
                        group = " ".join(sentences[i:i+2]).strip()
                        if len(group) >= 30 and len(group.split()) >= 4:
                            paragraphs.append({
                                "page": page_num,
                                "text": group
                            })
                    continue

            paragraphs.append({
                "page": page_num,
                "text": cleaned
            })

    return paragraphs


# ---------------------------------------------------------------------------
# STEP 3: TF-IDF Vectorization & Cosine Similarity Matching
# ---------------------------------------------------------------------------
def find_relevant_paragraphs_tfidf(paragraphs, query, top_n=TOP_N_RESULTS, threshold=SIMILARITY_THRESHOLD):
    """
    Uses Scikit-Learn's TfidfVectorizer and Cosine Similarity to find
    paragraphs semantically and syntactically closest to the search topic.
    
    How it works:
    1. TF-IDF converts text documents into numerical vectors based on term
       frequency and inverse document frequency across the corpus.
    2. Cosine Similarity calculates the cosine of the angle between the query
       vector and each paragraph vector:
          Cosine_Sim(A, B) = (A . B) / (||A|| * ||B||)
    3. Scores range from 0.0 (no similarity) to 1.0 (exact match).
    """
    if not paragraphs or not query.strip():
        return []

    paragraph_texts = [p["text"] for p in paragraphs]
    all_texts = paragraph_texts + [query]

    try:
        # Use unigrams and bigrams with English stop-word removal for richer semantic context
        vectorizer = TfidfVectorizer(
            stop_words='english',
            ngram_range=(1, 2),
            sublinear_tf=True
        )
        tfidf_matrix = vectorizer.fit_transform(all_texts)

        # The last vector in tfidf_matrix corresponds to the user query
        query_vector = tfidf_matrix[-1]
        paragraph_vectors = tfidf_matrix[:-1]

        # Compute cosine similarity between query and all paragraphs
        similarities = cosine_similarity(query_vector, paragraph_vectors).flatten()

        # Rank paragraphs by descending similarity score
        ranked_indices = similarities.argsort()[::-1]

        results = []
        for idx in ranked_indices:
            score = float(similarities[idx])
            if score >= threshold:
                results.append({
                    "text": paragraphs[idx]["text"],
                    "page": paragraphs[idx]["page"],
                    "score": round(score, 4),
                    "match_type": "TF-IDF Semantic Match"
                })
            if len(results) >= top_n:
                break

        return results
    except Exception as e:
        logging.warning(f"TF-IDF calculation issue: {e}")
        return []


# ---------------------------------------------------------------------------
# STEP 4: Fallback Keyword Search (Case-Insensitive Exact & Partial Match)
# ---------------------------------------------------------------------------
def find_relevant_paragraphs_fallback(paragraphs, query, top_n=TOP_N_RESULTS):
    """
    Fallback mechanism if TF-IDF score is zero or under threshold.
    Searches for exact or token-based matches of the topic keywords in paragraphs.
    """
    if not paragraphs or not query.strip():
        return []

    query_tokens = [re.escape(tok.lower()) for tok in query.strip().split() if len(tok) > 2]
    if not query_tokens:
        query_tokens = [re.escape(query.strip().lower())]

    pattern = re.compile(r'|'.join(query_tokens), re.IGNORECASE)

    matched = []
    for p in paragraphs:
        text = p["text"]
        matches = list(pattern.finditer(text))
        if matches:
            # Score based on frequency of occurrences
            score = min(0.99, 0.10 * len(matches))
            matched.append({
                "text": text,
                "page": p["page"],
                "score": round(score, 4),
                "match_count": len(matches),
                "match_type": "Keyword Match (Fallback)"
            })

    # Sort by match frequency descending
    matched.sort(key=lambda x: x["match_count"], reverse=True)
    return matched[:top_n]


# ---------------------------------------------------------------------------
# STEP 5: Keyword Highlighting for Frontend Display
# ---------------------------------------------------------------------------
def highlight_keywords_in_text(text: str, query: str) -> str:
    """
    Safely highlights query keywords in the given text by wrapping them
    in <mark class="highlight"> tags. Escapes HTML to prevent XSS.
    """
    escaped_text = html.escape(text)
    words = [w.strip() for w in query.split() if len(w.strip()) > 1]
    
    # Also include the full phrase
    terms_to_highlight = [query.strip()] + words
    terms_to_highlight = list(set([t for t in terms_to_highlight if t]))
    terms_to_highlight.sort(key=len, reverse=True)  # Longest matches first

    if not terms_to_highlight:
        return escaped_text

    pattern = re.compile(
        r'(' + '|'.join(re.escape(term) for term in terms_to_highlight) + r')',
        re.IGNORECASE
    )

    return pattern.sub(r'<mark class="highlight">\1</mark>', escaped_text)


# ---------------------------------------------------------------------------
# Core Processing Pipeline for a Single PDF
# ---------------------------------------------------------------------------
def process_pdf_document(pdf_path: str, filename: str, query: str):
    """
    Executes the full pipeline for one PDF:
    Extraction -> Chunking -> TF-IDF Search -> Fallback Search -> Highlighting.
    """
    pages_data, total_pages = extract_text_from_pdf(pdf_path)

    if not pages_data:
        return {
            "filename": filename,
            "total_pages": total_pages,
            "total_paragraphs": 0,
            "found": False,
            "message": "Could not extract readable text from this PDF (it may be scanned images or password-protected).",
            "matches": []
        }

    paragraphs = segment_into_paragraphs(pages_data)

    if not paragraphs:
        return {
            "filename": filename,
            "total_pages": total_pages,
            "total_paragraphs": 0,
            "found": False,
            "message": "No standard text paragraphs found in this document.",
            "matches": []
        }

    # Step 1: Try TF-IDF vectorization + cosine similarity
    matches = find_relevant_paragraphs_tfidf(paragraphs, query, top_n=TOP_N_RESULTS)

    # Step 2: Fallback to keyword matching if TF-IDF yielded no results
    if not matches:
        matches = find_relevant_paragraphs_fallback(paragraphs, query, top_n=TOP_N_RESULTS)

    # Step 3: Format and highlight matches
    formatted_matches = []
    for rank, m in enumerate(matches, start=1):
        formatted_matches.append({
            "rank": rank,
            "page": m["page"],
            "score": m["score"],
            "score_percentage": int(m["score"] * 100) if m["match_type"] == "TF-IDF Semantic Match" else "Keyword",
            "match_type": m["match_type"],
            "raw_text": m["text"],
            "highlighted_html": highlight_keywords_in_text(m["text"], query)
        })

    return {
        "filename": filename,
        "total_pages": total_pages,
        "total_paragraphs": len(paragraphs),
        "found": len(formatted_matches) > 0,
        "message": "Results extracted successfully" if formatted_matches else "No relevant content found for this topic.",
        "matches": formatted_matches
    }


# ---------------------------------------------------------------------------
# Web Routes & API Endpoints
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    """Renders the main web application UI."""
    return render_template('index.html')


@app.route('/api/extract', methods=['POST'])
def api_extract():
    """
    API endpoint handling multipart upload of up to 5 PDFs and a topic query.
    Returns JSON response containing ranked matches per PDF.
    """
    topic = request.form.get('topic', '').strip()
    if not topic:
        return jsonify({
            "success": False,
            "error": "Please enter a topic or keyword to search."
        }), 400

    uploaded_files = request.files.getlist('files')
    # Filter out empty entries
    valid_files = [f for f in uploaded_files if f and f.filename and is_allowed_file(f.filename)]

    if not valid_files:
        return jsonify({
            "success": False,
            "error": "Please select at least one valid PDF file (maximum 5)."
        }), 400

    if len(valid_files) > MAX_PDF_COUNT:
        return jsonify({
            "success": False,
            "error": f"You can upload a maximum of {MAX_PDF_COUNT} PDFs at a time."
        }), 400

    results = []
    
    # Process each PDF using a temporary directory for clean isolation
    with tempfile.TemporaryDirectory() as temp_dir:
        for file_obj in valid_files:
            safe_name = secure_filename(file_obj.filename) or "document.pdf"
            temp_path = os.path.join(temp_dir, safe_name)
            file_obj.save(temp_path)

            doc_result = process_pdf_document(temp_path, safe_name, topic)
            results.append(doc_result)

    total_matches_count = sum(len(r["matches"]) for r in results)
    
    return jsonify({
        "success": True,
        "topic": topic,
        "total_files_analyzed": len(results),
        "total_matches_found": total_matches_count,
        "results": results
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "Multi-PDF Topic Extractor"})


# ---------------------------------------------------------------------------
# Application Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Runs the Flask server on local port 5001 (or 5000)
    print("==========================================================")
    print(" Multi-PDF Topic Extractor is running locally!")
    print(" Open your browser and navigate to: http://127.0.0.1:5001")
    print("==========================================================")
    app.run(host='127.0.0.1', port=5001, debug=True)
