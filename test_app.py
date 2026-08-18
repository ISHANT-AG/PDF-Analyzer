"""
Automated unit and integration test for Multi-PDF Topic Extractor.
Tests:
1. Module imports (Flask, pdfplumber, nltk, scikit-learn).
2. PDF text extraction from sample PDFs.
3. TF-IDF + Cosine similarity paragraph ranking.
4. Fallback keyword search for exact terms.
5. Search term highlighting.
6. Flask test client endpoint (/api/extract).
"""

import os
import unittest
from app import (
    app,
    extract_text_from_pdf,
    segment_into_paragraphs,
    find_relevant_paragraphs_tfidf,
    find_relevant_paragraphs_fallback,
    highlight_keywords_in_text,
    process_pdf_document
)

class TestMultiPdfTopicExtractor(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.sample_pdf1 = "sample_pdfs/Biology_Principles.pdf"
        self.sample_pdf2 = "sample_pdfs/Botany_Encyclopedia.pdf"
        self.sample_pdf3 = "sample_pdfs/Solar_Energy_Engineering.pdf"

    def test_sample_pdfs_exist(self):
        self.assertTrue(os.path.exists(self.sample_pdf1), "Biology sample PDF must exist")
        self.assertTrue(os.path.exists(self.sample_pdf2), "Botany sample PDF must exist")
        self.assertTrue(os.path.exists(self.sample_pdf3), "Solar sample PDF must exist")

    def test_pdf_extraction(self):
        pages_data, total_pages = extract_text_from_pdf(self.sample_pdf1)
        self.assertGreaterEqual(total_pages, 2)
        self.assertEqual(len(pages_data), total_pages)
        self.assertIn("Photosynthesis", pages_data[0]["text"])

    def test_paragraph_segmentation(self):
        pages_data, _ = extract_text_from_pdf(self.sample_pdf1)
        paragraphs = segment_into_paragraphs(pages_data)
        self.assertGreater(len(paragraphs), 0)
        # Check that page tracking is preserved
        self.assertTrue(all("page" in p and "text" in p for p in paragraphs))

    def test_tfidf_matching(self):
        pages_data, _ = extract_text_from_pdf(self.sample_pdf1)
        paragraphs = segment_into_paragraphs(pages_data)
        
        # Search for "chloroplasts light energy"
        matches = find_relevant_paragraphs_tfidf(paragraphs, "chloroplasts light energy", top_n=2)
        self.assertGreater(len(matches), 0)
        self.assertIn("score", matches[0])
        self.assertGreater(matches[0]["score"], 0.0)
        self.assertEqual(matches[0]["match_type"], "TF-IDF Semantic Match")

    def test_keyword_fallback(self):
        pages_data, _ = extract_text_from_pdf(self.sample_pdf1)
        paragraphs = segment_into_paragraphs(pages_data)
        
        # Search for a term that might be filtered or exact
        matches = find_relevant_paragraphs_fallback(paragraphs, "RuBisCO", top_n=2)
        self.assertGreater(len(matches), 0)
        self.assertIn("RuBisCO", matches[0]["text"])

    def test_keyword_highlighting(self):
        sample_text = "Photosynthesis is the fundamental biological process."
        highlighted = highlight_keywords_in_text(sample_text, "Photosynthesis")
        self.assertIn('<mark class="highlight">Photosynthesis</mark>', highlighted)

    def test_process_pdf_document_pipeline(self):
        res = process_pdf_document(self.sample_pdf1, "Biology_Principles.pdf", "Photosynthesis")
        self.assertTrue(res["found"])
        self.assertGreater(len(res["matches"]), 0)
        self.assertEqual(res["filename"], "Biology_Principles.pdf")

    def test_api_extract_endpoint(self):
        with open(self.sample_pdf1, 'rb') as f1, open(self.sample_pdf2, 'rb') as f2:
            data = {
                'topic': 'Photosynthesis',
                'files': [
                    (f1, 'Biology_Principles.pdf'),
                    (f2, 'Botany_Encyclopedia.pdf')
                ]
            }
            response = self.app.post('/api/extract', data=data, content_type='multipart/form-data')
            self.assertEqual(response.status_code, 200)
            res_json = response.get_json()
            self.assertTrue(res_json["success"])
            self.assertEqual(res_json["total_files_analyzed"], 2)
            self.assertGreaterEqual(res_json["total_matches_found"], 2)

    def test_api_validation_errors(self):
        # Empty topic
        res = self.app.post('/api/extract', data={'topic': ''}, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)

        # No files
        res2 = self.app.post('/api/extract', data={'topic': 'Test'}, content_type='multipart/form-data')
        self.assertEqual(res2.status_code, 400)


if __name__ == '__main__':
    unittest.main()
