# 📄 Multi-PDF Topic Extractor & Comparator

A lightweight, fully offline, privacy-first Python web application that allows users to upload multiple PDF documents (up to 5), search for any topic or keyword, and extract and compare the most relevant paragraphs side-by-side using **TF-IDF Vectorization** and **Cosine Similarity**.

---

## 🌟 Key Features

1. **Multi-PDF Text Extraction**: Extracts text page-by-page from up to 5 PDFs simultaneously using `pdfplumber`, tracking exact page numbers for every extracted passage.
2. **Semantic Paragraph Ranking**: Uses Scikit-Learn's `TfidfVectorizer` (with unigram and bigram tokenization and English stop-word filtering) combined with `cosine_similarity` to rank paragraphs by relevance.
3. **Keyword Fallback Mechanism**: If TF-IDF cosine similarity produces low or zero scores, an intelligent case-insensitive keyword scanner ensures verbatim mentions are never missed.
4. **Keyword Highlighting**: Automatically highlights search terms and topic phrases within the extracted text using visual `<mark>` tags.
5. **Interactive Side-by-Side Comparison**:
   - **Compare Side-by-Side Mode**: Multi-column comparison view to analyze how different authors/sources explain the same concept.
   - **Grid Mode**: Clean card layout with score tags, page indicators, and snippet copy buttons.
6. **Report Export**: Instant "Copy All" and 1-click Download Summary (`.txt`) for documentation or notes.
7. **100% Offline & Private**: Runs entirely locally on your machine with zero external API calls or internet dependencies.

---

## 🏗️ Project Architecture & Structure

```
PDF Analyzer/
├── app.py                  # Flask backend server, PDF processing & TF-IDF engine
├── templates/
│   └── index.html          # Clean, modern web UI with side-by-side comparison
├── static/
│   ├── style.css           # Glassmorphic dark theme, responsive grid/matrix styling
│   └── script.js           # Drag-and-drop uploads, async fetch, copy/export logic
├── requirements.txt        # Python dependency specifications
└── README.md               # Project documentation and viva explanation
```

---

## 🚀 Installation & Local Run Guide

### Prerequisites
- **Python 3.9+** (Tested with Python 3.9, 3.10, 3.11, 3.12, 3.13, 3.14)
- `pip` (Python package manager)

### Step 1: Clone or Navigate to the Project Folder
```bash
cd "PDF Analyzer"
```

### Step 2: (Recommended) Create and Activate a Virtual Environment
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Run the Application
```bash
python app.py
```

### Step 5: Open in Your Browser
Open your browser and visit:
```
http://127.0.0.1:5001
```

---

## 🧠 How It Works: TF-IDF & Cosine Similarity (Viva / Interview Guide)

This section explains the core NLP (Natural Language Processing) and Information Retrieval concepts used in this project in simple, easy-to-explain terms for project demos and viva examinations.

```
┌─────────────────┐       ┌────────────────────────┐       ┌─────────────────────────┐
│ Uploaded PDFs   │ ────> │ pdfplumber Extraction  │ ────> │ Paragraph Segmentation  │
└─────────────────┘       └────────────────────────┘       └────────────┬────────────┘
                                                                        │
┌─────────────────────────┐       ┌────────────────────────┐            │
│ Side-by-Side Comparison │ <──── │ Cosine Similarity      │ <──────────┘
│ UI with Highlighting    │       │ Ranking & Fallback     │
└─────────────────────────┘       └────────────────────────┘
```

### 1. Document Extraction & Paragraph Segmentation
- **Tool**: `pdfplumber`
- **Process**: Each PDF is read page-by-page. Raw text is normalized (hyphenated word breaks across newlines are joined, excess spaces removed) and segmented into discrete paragraphs while tagging the originating page number.

### 2. Term Frequency - Inverse Document Frequency (TF-IDF)
TF-IDF is a statistical numerical statistic that reflects how important a word is to a document in a collection.

$$\text{TF-IDF}(t, d, D) = \text{TF}(t, d) \times \text{IDF}(t, D)$$

#### A. Term Frequency ($\text{TF}$)
Measures how often a term $t$ appears in paragraph $d$:
$$\text{TF}(t, d) = \frac{\text{Count of } t \text{ in } d}{\text{Total words in } d}$$

#### B. Inverse Document Frequency ($\text{IDF}$)
Measures how rare or informative a term is across all paragraphs $D$:
$$\text{IDF}(t, D) = \ln\left(\frac{1 + |D|}{1 + |\{d \in D : t \in d\}|}\right) + 1$$
- Common filler words like *"is"*, *"the"*, *"and"* appear in almost all paragraphs, so their $\text{IDF} \approx 0$.
- Domain-specific terms like *"photosynthesis"*, *"chloroplast"*, or *"backpropagation"* appear in few paragraphs, so their $\text{IDF}$ is high.

### 3. Cosine Similarity Ranking
Once each paragraph and the user's search query are converted into multi-dimensional vectors ($\vec{A}$ and $\vec{B}$), we compute the **cosine of the angle** between them:

$$\text{Cosine Similarity}(\vec{A}, \vec{B}) = \frac{\vec{A} \cdot \vec{B}}{\|\vec{A}\| \|\vec{B}\|} = \frac{\sum_{i=1}^n A_i B_i}{\sqrt{\sum_{i=1}^n A_i^2} \sqrt{\sum_{i=1}^n B_i^2}}$$

- **Score Range**: $0.0$ (completely orthogonal / unrelated) to $1.0$ (identical direction / highest relevance).
- **Advantage over Euclidean Distance**: Cosine similarity is independent of paragraph length—a short paragraph and a long paragraph covering the same topic will have high similarity.

### 4. Intelligent Fallback Strategy
If a query contains domain words omitted from the vectorizer or produces a cosine score of $0.0$, the system automatically switches to a regex-based case-insensitive token scanner. This guarantees zero false negatives for explicit mentions.

---

## 🎓 Frequently Asked Questions for College Viva

| Viva Question | Concise Answer |
| :--- | :--- |
| **Why use `pdfplumber` over `PyPDF2`?** | `pdfplumber` uses `pdfminer.six` under the hood, offering significantly better layout preservation, line spacing fidelity, and extraction accuracy than basic `PyPDF2`. |
| **Why TF-IDF instead of simple string matching (`in` / regex)?** | TF-IDF scores paragraphs based on term relevance and contextual vocabulary (using unigrams and bigrams with stop-word removal), ranking richer paragraphs higher rather than just checking boolean presence. |
| **Why not heavy LLM embeddings (e.g. OpenAI / BERT)?** | TF-IDF runs with zero API cost, executes in milliseconds, works 100% offline without GPUs, and has zero data privacy concerns for sensitive PDF documents. |
| **What happens if a PDF is a scanned image?** | `pdfplumber` extracts digital text streams. For scanned image PDFs without OCR text layers, the app gracefully flags that no readable text stream was found. |

---

## 🛠️ Technology Stack

- **Backend**: Python 3, Flask, Werkzeug
- **PDF Extraction**: `pdfplumber`
- **Text Processing & Vectorization**: `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`), `nltk`
- **Frontend**: HTML5, Vanilla CSS3 (Custom Glassmorphism Design System), JavaScript (ES6+)

---

## 📄 License
Open source for educational and academic mini-project demonstrations.
# PDF-Analyzer
