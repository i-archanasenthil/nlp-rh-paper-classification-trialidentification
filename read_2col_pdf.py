import fitz
import re
import os

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
        #ClinicalTrials.gov
        r'\bNCT\d{6,8}\b', 
        #EU CT Register
        r'\bEUCTR\d{4}-\d{6}-\d{2}(?:-[A-Z]{2,3})?\b',
        r'\bEudraCT\s?\d{4}-\d{6}-\d{2}\b',
        #ISRCTN
        r'\bISRCTN\d{6,8}\b',
        #UMIN (Japan)
        r'\bUMIN\d{6,8}\b',
        #ChiCTR(China)
        r'\bChiCTR(?:-[A-Z]{2,3})?-\d{6,8}\b',
        #ACTRN(Australia/New Zealand)
        r'\bACTRN\d{14}\b',
        #JPRN(Japan)
        r'\bJPRN-[A-Z]+\d{6,8}\b',
        #Japic(Japan)
        r'\bJapicCTI-\d{6}\b',
        #CTRI(India)
        r'\bCTRI/\d{4}/\d{2}/\d{6}\b',
        #IRCT(Iran)
        r'\bIRCT\d{8,15}(?:[A-Z]\d+)?\b',
        r'\bIRCT/\d{4}/\d{2}/\d{2}/\d+\b'
        #DRKS(Germany)
        r'\bDRKS\d{6,8}\b',
        #NTR(Netherlands)
        r'\bNTR\d{4,8}\b',
        #PER(Peru)
        r'\bPER-\d{3,4}-\d{2}\b',
        #KCT(Korea)
        r'\bKCT\d{6,8}\b',
        #SLCTR(Sri Lanka),
        r'\bSLCTR/\d{4}/\d{3}\b',
        #ReBec(Brazil)
        r'\bRBR-[A-Za-z0-9]{6,10}\b',
        #PACTR(Pan African)
        r'\bPACTR\d{14,20}\b',
        #TCTR(Thailand)
        r'\bTCTR\d{13}\b',
        #CRiS(Korea Clinical Research Info Service)
        r'\bCRiS-KCT\d{7}\b',
        #LBCTR(Lebanan)
        r'\bLBCTR\d{8,12}\b',
        #Health Canada Clinical Trials database
        r'\bHC-CTD-\d{4}-\d{4}\b',
        #WHO Universal Trial Number
        r'\bU1111-\d{4}-\d{4}\b',
        #Ukraine - UCTR
        r'\bUCTR\d{11,15}\b',
        r'\bUCTR-\d{5,7}\b'
    ]

    trial_ids = []

    for pattern in patterns: 
        trial_ids += re.findall(pattern, text)

    return list(set(trial_ids))

def extract_from_pdf_or_text(input_source: str):
    """
    Automatically detects whether the input is a path to the pdf file or plain text
    If input source is a valid PDF file(ends with .pdf), it reads and extracts text from it
    Otherwise, treats input_source as raw_text
    """
    if os.path.isfile(input_source) and input_source.lower().endswith('.pdf'):
        print("Detected Input PDF file:", input_source)
        text = extract_text_two_cols(pdf_path)
    else:
        print("Detected raw text input")
        text = input_source

    trial_ids = extract_trial_ids(text)
    return trial_ids

if __name__ == "__main__":
    pdf_path = "data/paper2.pdf"
    trial_ids_pdf = extract_from_pdf_or_text(pdf_path)
    print("Extracted from PDF:", trial_ids_pdf)

    sample_text = """
    Background: The objective of this study was to evaluate the efficacy and safety of SC golimumab (GLM) in RA pts who previously received IV GLM q12 wks with and without MTX. 
    Methods: Adult RA pts (n=643), with persistent disease activity while receiving MTX>15 mg/wk for at least 3mos, were randomized to IV placebo+MTX (n=129) or GLM 2- or 4 mg/kg, both with and without MTX, q12wks (n=514) up to Wk96 [median 68.4 wks]. 
    Pts who received IV GLM completing the Wk48 database lock were eligible to participate in the long term extension (LTE) and receive open label GLM 50mg SC q4wks for an additional 24wks (E-0 to E-24) and 16wks of safety follow-up (E-24 to E-40) with and without MTX. 
    At Wk E-14, changes in concomitant RA medication (including MTX) were permitted at the investigators discretion. 
    Results: Of the 505 pts who entered the LTE, 186 pts who did not change dosing strategy during the IV phase (GLM IV 2 mg/kg IV+MTX [n=82]; GLM IV 4 mg/kg+MTX [n=104]) participated in the LTE at Wk E-0; baseline demographics and disease characteristics were comparable between both groups. 
    Through Wk E-0, ACR20, ACR50, and DAS28-CRP (good or moderate) response was achieved by 67.5%, 61.9%, 43.4% and 39.2%, 87.7% 82.1% in the IV GLM 2 mg/ kg and 4 mg/kg groups, respectively. 
    Overall efficacy (ACR20, ACR50) and improvements in ACR components were sustained or improved in a majority of pts through Wk E-24 regardless of GLM IV dose: ACR20 was achieved by 85.7% IV GLM 2 mg/kg patients and 90.8% IV GLM 4 mg/kg patients, ACR50 was achieved by 77.8% and 82.1%, respectively. 
    Compared with the IV phase, DAS 28 response and CRP measures improved with SC GLM. 
    The rates of GLM SC discontinuations from Wk E-0 through Wk E-24 were 2.4% and 4.8% in pts previously treated with IV GLM 2- and 4 mg/kg, respectively, most commonly for adverse events (AEs). 
    A total of 77.5% and 83.0% of patients in the GLM IV 2- and 4mg/kg groups, respectively, experienced >1 AEs through Wk E-0. Rates of infusion reactions remained lower in GLM-treated pts compared with placebotreated pts. 
    During the LTE (Wk E-0 through Wk E-40), 69.5% of SC GLM-treated pts experienced >1 AE; 13.7% and 14.0% of pts previously treated with GLM IV 2- and 4 mg/kg, respectively, experienced >1 serious AE. 
    Injection site reactions were rare [0.6% (19/3443)]. 
    Conclusions: In pts switched to SC GLM 50mg through the LTE, overall efficacy was sustained or improved regardless of whether pts previously received IV GLM 2-or 4 mg/kg. 
    Both IV and SC GLM were well tolerated with acceptable safety profiles. NCT00361335
    """

    trial_ids_text = extract_from_pdf_or_text(sample_text)
    print("Extracted from text:", trial_ids_text)
