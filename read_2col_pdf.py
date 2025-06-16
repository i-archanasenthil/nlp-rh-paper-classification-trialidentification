import fitz
import re

def is_full_width(block, page_width, threshold=0.8):
    """
    Check if the block spans for the entire page width
    Like title, some abstracts, tables, graphs

    The bounding box (bbox) helps identify the layout structure, ignore headers and footers 
    reconstruct reading order and extract elements
    """
    x0, y0, x1, y1 = block["bbox"]
    width = x1 -x0
    return width >= page_width*threshold

def is_header_or_footer(block, page_height, margin = 25):
    """
    Identifies if the block is a header or the footer area
    The margin decides how much of the top and bottom has to be ignored
    """
    y0, y1 = block["bbox"][1], block["bbox"][3]
    return y1 < margin or y0 > (page_height - margin)

def is_table_like(block, digit_threshold=0.3, line_threshold=3):
    """
    Check if the content has high digit ratio or many numbers
    see if the content has many short lines that are aligned
    The block is likely a table
    """
    lines = block["lines"]
    
    if len(lines) < line_threshold:
        return False

    text_content = [span["text"] for line in lines for span in line["spans"] if "text" in span]
    all_text = " ".join(text_content)
    if not all_text:
        return False
    digit_ratio = sum(c.isdigit() for c in all_text) / len(all_text)
    return digit_ratio > digit_threshold

def block_text(block):
    """
    Convert a block of text with lines and spans into plain text
    """
    lines = block.get("lines",[])
    texts = []
    for line in lines:
        line_text = " ".join(span['text'] for span in line.get("spans", []))
        texts.append(line_text)
    return "\n".join(texts)

def extract_text_two_cols(pdf_path):
    """
    Read content from the URL 
    This case reads content from the PDFs
    """
    doc = fitz.open(pdf_path)
    full_text = ""

    """
    read the content returns as a dictionary version of the page number and the contents of the page organized as blocks
    type == 0 means text block only
    the line ignores images, drawings and tables 
    """
    for page_num, page in enumerate(doc):
        blocks = [
            b for b in page.get_text("dict")["blocks"] 
            if b["type"] == 0 
            and not is_header_or_footer(b, page.rect.height)
            and not is_table_like(b)
            ]
        #Getting the width of the page
        page_width = page.rect.width

        """
        separating the contents with full-width and two column blocks
        """
        col_blocks = []

        for b in blocks:
            if is_header_or_footer(b, page.rect.height):
                continue
            if is_table_like(b):
                continue
            col_blocks.append(b)
        
        left_col = []
        right_col = []

        for b in col_blocks:
            x0, y0, x1, y1 = b["bbox"]
            center_x = (x0 + x1) / 2
            if center_x < page.rect.width / 2:
                left_col.append(b)
            else:
                right_col.append(b)
        
        left_col.sort(key = lambda b: b["bbox"][1])
        right_col.sort(key = lambda b: b["bbox"][1])

        page_text = ""
        for b in left_col + right_col:
            page_text += block_text(b) + "\n\n"
    
        full_text += f"\n--- Page {page_num + 1} ---\n" +page_text        

    return full_text

def extract_trial_ids(text: str):
    """
    match the most common patterns of the clinical trial identfiers 
    """
    patterns = [
        r'\bNCT\d{6,8}\b',
        r'\bEUCTR\d{4}-\d{6}-\d{2}(?:-[A-Z]{2,3})?\b',
        r'\bISRCTN\d{6,8}\b',
        r'\bUMIN\d{6,8}\b',
        r'\bChiCTR(?:-[A-Z]{2,3})?-\d{6,8}\b',
        r'\bACTRN\d{14}\b',
        r'\bJPRN-[A-Z]+\d{6,8}\b',
        r'\bJapicCTI-\d{6}\b',
        r'\bCTRI/\d{4}/\d{2}/\d{6}\b',
        r'\bIRCT\d{8,15}(?:[A-Z]\d+)?\b',
        r'\bDRKS\d{6,8}\b',
        r'\bNTR\d{4,8}\b',
        r'\bPER-\d{3,4}-\d{2}\b',
        r'\bKCT\d{6,8}\b',
        r'\bEudraCT\s?\d{4}-\d{6}-\d{2}\b'
    ]

    trial_ids = []

    for pattern in patterns: 
        trial_ids += re.findall(pattern, text)

    return list(set(trial_ids))

#if __name__ == "main":
print("reading paper")
pdf_path = "data/paper2.pdf"
text = extract_text_two_cols(pdf_path)
print(text)
trial_ids = extract_trial_ids(text)
print("Extracted Clinical Trial IDs:", trial_ids)
