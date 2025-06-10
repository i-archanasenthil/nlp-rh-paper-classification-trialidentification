import fitz

def is_full_width(block, page_width, threshols=0.8):
    """
    Check if the block spans for the entire page width
    Like title, some abstracts, tables, graphs

    The bounding box (bbox) helps identify the layout structure, ignore headers and footers 
    reconstruct reading order and extract elements
    """
    x0, y0, x1, y1 = block["bbox"]
    width = x1 -x0
    return width >= page_width*threshold

def is_header_or_footer(block, page_height, margin = 50):
    """
    Identifies if the block is a header or the footer area
    The margin decides how much of the top and bottom has to be ignored
    """
    y0, y1 = block["bbbox"][1], block["bbox"][3]
    return y1 < margin or y0 > (page_height - margin)

def extraxt_text_two_cols(pdf_path):
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
        blocks = [b for b in page.get_text("dict")["blocks"] if b["type"] == 0] and not is_header_or_footer(b, page.rect_height)
        #Getting the width of the page
        page_width = page.rect.width

        """
        separating the contents with full-width and two column blocks
        """
        full_width_blocks = []
        col_blocks = []

        for b in blocks:
            if is_full_width(b, page_width):
                full_width_blocks.append(b)
            else:
                col_blocks.append(b)

        """
        Sort all these blocks in a vertical blocks for easy readability
        Need to have content in full_width and two-column 
        blocks between based on vertical position
        Adding a dummy block to add at the end of the page
        """
        full_width_blocks.sort(key= lambda b: b["bbox"][1])
        col_blocks.sort(key= lambda b: b["bbox"][1])

        sentinel_block = {"bbox" : [0, page.rect.height + 1, page_width, page_rect.height + 2]}
        full_width_blocks.append(sentinel_block)

        #Initializes pointer to keep track of which column block 
        col_idx = 0

        def block_text(block):
            """
            block is made of lines. function goes through each line in a block
            spans are portion of text with the same style. Combines all spans in the line into a single line of text
            Joins all these lines together with \n to preserve paragraph structure            
            """
            lines = block["lines"]
            texts = []
            for line in lines:
                line_text = " ".join(span["text"] for span in line["spans"])
                texts.append(line_text)
            return "\n".join(texts)

        page_text = ""
        
        for i in range(len(full_width_blocks)-1):
            current_fw = full_width_blocks[i]
            next_fw = full_width_blocks[i+1]

            page_text += block_text(current_fw) + "\n\n"
            """
            Collect all the two column text between the two full_width_blocks and define the vertical slice
            Loop through the column block and collect those that fall within the vertical slice
            """
            slice_blocks = []
            while col_idx < len(col_blocks) and col_blocks[col_idx]["bbox"][1] >= lower_y and col_blocks[col_idx]["bbox"][1] < upper_y:
                slice_blocks.append(col_blocks[col_idx])
                col_idx += 1

            """
            The content between is split into two blocks left column and the right column
            Sorting the blocks vertically to appear in the top to bottom order,
            """
            left_col = []
            right_col = []
            for b in slice_blocks:
                x0, y0, x1, y1 = b["bbox"]
                center_x = (x0 + x1) / 2
                if center_x < page_width / 2:
                    left_col.append(b)
                else:
                    right_col.append(b)

            left_col.sort(key = lambda b:b["bbox"][1])
            right_col.sort(key = lambda b: b["bbox"][1])

            for b in left_col + right_col:
                page_text += block_text(b) + "\n\n"

        full_text += f"\n--- Page {page_num + 1} ---\n" + page_text
    return full_text

if __name__ == "main":
    pdf_path = "\data\paper1.pdf"
    text = extract_text_two_cols(pdf_path)
    print(text[:3000])

