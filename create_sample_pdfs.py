"""
Utility script to generate sample test PDFs for testing Multi-PDF Topic Extractor.
Uses pure Python with standard PDF specification (no external PDF creation library required).
"""

import os

def create_simple_pdf(filename: str, title: str, pages_paragraphs: list):
    """
    Creates a valid standard PDF 1.4 file containing the given paragraphs across pages.
    """
    objects = []
    
    def add_object(content):
        objects.append(content)
        return len(objects)

    # We will build objects sequentially
    # Object 1: Catalog
    # Object 2: Outlines
    # Object 3: Pages tree
    # Object 4: Font
    # Subsequent objects: Page objects and Content stream objects
    
    font_obj_idx = 4
    pages_count = len(pages_paragraphs)
    
    page_obj_indices = []
    content_obj_indices = []
    
    # We will assign indices
    # 1: Catalog, 2: Outlines, 3: Pages, 4: Font
    current_idx = 5
    for _ in range(pages_count):
        page_obj_indices.append(current_idx)
        current_idx += 1
        content_obj_indices.append(current_idx)
        current_idx += 1

    # Object 1: Catalog
    catalog = f"1 0 obj\n<< /Type /Catalog /Pages 3 0 R /Outlines 2 0 R >>\nendobj\n"
    # Object 2: Outlines
    outlines = f"2 0 obj\n<< /Type /Outlines /Count 0 >>\nendobj\n"
    # Object 3: Pages
    kids_str = " ".join([f"{idx} 0 R" for idx in page_obj_indices])
    pages_tree = f"3 0 obj\n<< /Type /Pages /Count {pages_count} /Kids [ {kids_str} ] >>\nendobj\n"
    # Object 4: Font
    font_def = f"4 0 obj\n<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica >>\nendobj\n"

    all_objs = [catalog, outlines, pages_tree, font_def]

    for p_idx in range(pages_count):
        page_idx = page_obj_indices[p_idx]
        content_idx = content_obj_indices[p_idx]
        paragraphs = pages_paragraphs[p_idx]
        
        # Build text stream
        # PDF BT ... ET stream
        stream_lines = ["BT", "/F1 12 Tf", "50 750 Td", "16 TL"]
        
        # Add title on page 1
        if p_idx == 0:
            stream_lines.append(f"({title}) Tj")
            stream_lines.append("T*")
            stream_lines.append("T*")

        for para in paragraphs:
            # Escape parenthesis in PDF strings
            escaped = para.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            # Break long paragraph into ~70 char lines for PDF text display
            words = escaped.split()
            current_line = []
            for w in words:
                current_line.append(w)
                if len(" ".join(current_line)) > 65:
                    stream_lines.append(f"({' '.join(current_line)}) Tj")
                    stream_lines.append("T*")
                    current_line = []
            if current_line:
                stream_lines.append(f"({' '.join(current_line)}) Tj")
                stream_lines.append("T*")
            stream_lines.append("T*") # extra line break between paragraphs

        stream_lines.append("ET")
        stream_content = "\n".join(stream_lines)
        stream_len = len(stream_content.encode('latin1'))

        # Page Object
        page_obj = f"{page_idx} 0 obj\n<< /Type /Page /Parent 3 0 R /MediaBox [ 0 0 612 792 ] /Contents {content_idx} 0 R /Resources << /ProcSet [ /PDF /Text ] /Font << /F1 4 0 R >> >> >>\nendobj\n"
        # Content Stream Object
        content_obj = f"{content_idx} 0 obj\n<< /Length {stream_len} >>\nstream\n{stream_content}\nendstream\nendobj\n"

        all_objs.append(page_obj)
        all_objs.append(content_obj)

    # Build final PDF binary
    header = "%PDF-1.4\n"
    body = ""
    xref_offsets = [0] # 0 offset
    current_pos = len(header.encode('latin1'))

    for obj_str in all_objs:
        xref_offsets.append(current_pos)
        encoded = obj_str.encode('latin1')
        current_pos += len(encoded)
        body += obj_str

    xref_pos = current_pos
    xref = f"xref\n0 {len(xref_offsets)}\n0000000000 65535 f \n"
    for off in xref_offsets[1:]:
        xref += f"{off:010d} 00000 n \n"

    trailer = f"trailer\n<< /Size {len(xref_offsets)} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"

    full_pdf = header + body + xref + trailer
    with open(filename, 'wb') as f:
        f.write(full_pdf.encode('latin1'))
    print(f"Generated sample PDF: {filename}")


if __name__ == '__main__':
    sample_dir = "sample_pdfs"
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Biology_Campbell_Extract.pdf
    create_simple_pdf(
        os.path.join(sample_dir, "Biology_Principles.pdf"),
        "Biology Principles - Chapter 8: Energy and Life",
        [
            [
                "Photosynthesis is the fundamental biological process by which autotrophic organisms convert light energy into chemical energy stored in glucose molecules. In green plants, this conversion takes place primarily inside specialized organelles called chloroplasts.",
                "The thylakoid membranes contain chlorophyll pigments that absorb blue and red wavelengths while reflecting green light. During the light-dependent reactions, water molecules are split through photolysis, releasing molecular oxygen as a vital byproduct.",
                "Cellular respiration operates conversely by breaking down carbohydrates in mitochondria to yield adenosine triphosphate (ATP) for cellular work."
            ],
            [
                "The Calvin cycle, also known as the light-independent reactions, occurs within the stroma of chloroplasts. Carbon dioxide is captured through carbon fixation catalyzed by the enzyme RuBisCO, ultimately producing glyceraldehyde 3-phosphate (G3P).",
                "Environmental factors such as ambient temperature, carbon dioxide concentration, and light irradiance substantially influence photosynthetic efficiency and overall agricultural crop yields."
            ]
        ]
    )

    # 2. Botany_Encyclopedia.pdf
    create_simple_pdf(
        os.path.join(sample_dir, "Botany_Encyclopedia.pdf"),
        "Encyclopedia of Plant Science - Photosynthetic Pathways",
        [
            [
                "Photosynthesis sustains almost all higher life forms on Earth by fueling the base of ecological food webs and generating atmospheric oxygen. Plants utilize solar radiation to drive the reduction of carbon dioxide into organic starch and sugars.",
                "C3, C4, and CAM pathways represent evolutionary adaptations in plant physiology to maximize carbon assimilation under varying moisture, temperature, and arid environmental stresses.",
                "Stomata on the underside of plant leaves regulate transpiration and gas exchange, allowing carbon dioxide intake while minimizing water vapor loss during intense sunlight."
            ]
        ]
    )

    # 3. Solar_Physics_Review.pdf
    create_simple_pdf(
        os.path.join(sample_dir, "Solar_Energy_Engineering.pdf"),
        "Solar Energy Engineering - Photovoltaic Systems",
        [
            [
                "Photovoltaic systems directly convert electromagnetic solar radiation into electrical power utilizing semiconductor materials exhibiting the photovoltaic effect. Silicon solar cells remain the dominant commercial technology.",
                "Artificial photosynthesis aims to mimic natural biological light harvesting to produce clean hydrogen fuel and synthetic hydrocarbons through photocatalytic water splitting.",
                "Quantum dot solar cells and perovskite multi-junction architectures offer exciting pathways toward exceeding the theoretical Shockley-Queisser limit for single-junction energy conversion."
            ]
        ]
    )
