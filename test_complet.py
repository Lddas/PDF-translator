import fitz
import tabula
from transformers import pipeline

translator = pipeline("translation_en_to_fr", model="t5-base")

#-----------------------------------------------------------------------------
#PDF extraction

def extract_text_with_positions(pdf_path, tabs_info):
    doc = fitz.open(pdf_path)
    text_info = tabs_info #To start, we copy the tabs info since there are not in the document anymore
    for page_num, page in enumerate(doc):
        if page_num not in text_info:
            text_info[page_num] = []
        blocks = page.get_text("dict")["blocks"]
        for block in blocks:
            if block['type'] == 0:
                combined_text = ""
                block_info = []
                is_title = False
                tab_values = [False, 0, 0, 0, []]
                for line in block['lines']:
                    for span in line['spans']:
                        text = span['text']
                        x0, y0 = span['bbox'][:2]
                        font_name = span['font']
                        font_size = span['size']
                        if font_size >= 14:
                            is_title = True
                        flags = flags_decomposer(span["flags"])
                        if 'bold' in flags and 'italic' in flags:
                            base_font = 'hebi'
                        elif 'bold' in flags:
                            base_font = 'hebo'
                        elif 'italic' in flags:
                            base_font = 'heit'
                        else:
                            base_font = 'helv'
                        color = fitz.sRGB_to_rgb(span["color"])
                        color = tuple(c / 255 for c in color)
                        pos = (x0, y0)
                        combined_text += text + " "
                        block_info.append((text, pos, base_font, font_size, color, is_title, tab_values))
                text_info[page_num].append((combined_text.strip(), block_info))
    doc.close()
    return text_info
#Full text + separate text pour les flags


def flags_decomposer(flags):
    """Make font flags human readable."""
    l = []
    if flags & 2 ** 0:
        l.append("superscript")
    if flags & 2 ** 1:
        l.append("italic")
    if flags & 2 ** 2:
        l.append("serifed")
    else:
        l.append("sans")
    if flags & 2 ** 3:
        l.append("monospaced")
    else:
        l.append("proportional")
    if flags & 2 ** 4:
        l.append("bold")
    return l

#-----------------------------------------------------------------------------
#translation

def translate_text(text_blocks):
    translated_blocks = []
    for combined_text, block_info in text_blocks:
        translated = translator(combined_text, max_length=512)[0]['translation_text']
        translated_blocks.append((translated, block_info))
    return translated_blocks

#-----------------------------------------------------------------------------
#creation pdf

def create_translated_pdf(input_pdf, output_pdf, image_info, tables, translated_blocks):
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()
    
    for page_num, page in enumerate(doc):
        rect_page = page.rect
        new_page = new_doc.new_page(width=rect_page.width, height=rect_page.height)
        index_row = 0
        index_col = 0
        index_tab = 0
        col_width = 0
        col_values = []
        offset_col = 0
        for translated_text, block_info in translated_blocks[page_num]:
            tab_values = block_info[0][6]
            x0, y0 = block_info[0][1]  # Position of the first word in the block
            y_offset = y0  # Start from the original vertical position of the block
            x_offset = x0
            words = translated_text.split()
            span_index = 0
            if not tab_values[0]:                
                #method 
                #We write block by block 
                #x0 = beginning block
                #x0_offset = beginning current word
                #We take the first x0, then we write one word after the other 
                #    (we dont consider the original words pos anymore bc it changes with translation)
                # Exceptions for : title (we dont want to go to the line even if it is longer than before)
                #                  tabs (we dont want one after this other, but all at same position)
                for word in words:
                    if span_index >= len(block_info):
                        # If we run out of spans, use the last span's formatting
                        original_text, pos, base_font, font_size, color, is_title, tab_values = block_info[-1]
                    else:
                        original_text, pos, base_font, font_size, color, is_title, tab_values = block_info[span_index]

                    text_width = fitz.get_text_length(word, fontname=base_font, fontsize=font_size)
                    
                    if is_title and x_offset + text_width > rect_page.width:
                        x_offset = x0
                        y_offset += font_size * 1.2  # Adjust line height based on font size
                    elif not is_title and x0 + x_offset + text_width > rect_page.width:  # Check if the word fits in the current line (x0 acts as right margin and offset as line+left margin)
                        x_offset = x0
                        y_offset += font_size * 1.2  # Adjust line height based on font size

                    new_page.insert_text((x_offset, y_offset), word, fontname=base_font, fontsize=font_size, color=color)
                    x_offset += text_width + fitz.get_text_length(" ", fontname=base_font, fontsize=font_size)

                    # Only increment the span index if the word fits within the original span
                    if span_index < len(block_info) and x_offset >= pos[0] + fitz.get_text_length(original_text, fontname=base_font, fontsize=font_size):
                        span_index += 1

                y_offset += font_size * 1.2

            else: #for tabs, we dont need conditions on line width. We just respect original positions
                original_text, pos, base_font, font_size, color, is_title, tab_values = block_info[0]
                m = tab_values[1]
                n = tab_values[2]
                tab_nb = tab_values[3]
                tab_bbox = tab_values[4]
                cells = fitz.make_table(tab_bbox, cols=n, rows=m)
                
                text_width = fitz.get_text_length(translated_text, fontname=base_font, fontsize=font_size)

                if index_tab == tab_nb: #useless si on construit column par column
                    if index_col < n: #iterate trough rows
                        if index_col == 0 and index_row == 0:
                            offset_col = tab_bbox[0]
                        col_values.append([translated_text, block_info])
                        index_row += 1
                        if text_width > col_width:
                            col_width = text_width #We find the largest cell   

                        if index_row == m: #iterate trough columns
                            col_width = col_width + 10 #margin
                            index_row = 0

                            for i, values in enumerate(col_values):
                                text = values[0]
                                original_text, pos, base_font, font_size, color, is_title, tab_values = values[1][0]
                                text_width = fitz.get_text_length(text, fontname=base_font, fontsize=font_size)
                                x0 = offset_col + (col_width - text_width) / 2
                                y0 = pos[1]
                                new_page.insert_text((x0, y0), text, fontname=base_font, fontsize=font_size, color=color)
                                # Draw bottom line
                                #new_page.draw_line((offset_col, y0 + 10), (offset_col + col_width, y0 + 10))
                                
                                # Draw top line
                                new_page.draw_line((offset_col, cells[i][index_col][1]), (offset_col + col_width, cells[i][index_col][1]))
                                # draw bottom line
                                new_page.draw_line((offset_col, cells[i][index_col][3]), (offset_col + col_width, cells[i][index_col][3]))
                                # Draw left line
                                new_page.draw_line((offset_col, cells[i][index_col][1]), (offset_col, cells[i][index_col][3]))
                                # Draw right line
                                new_page.draw_line((offset_col + col_width, cells[i][index_col][1]), (offset_col + col_width, cells[i][index_col][3]))

                            index_col += 1
                            offset_col += col_width
                            col_values = []                          

                    else:
                        index_col = 0
                        index_row = 0
                        index_tab += 1

                        cells = fitz.make_table(tab_bbox, cols=n, rows=m)


    # Add images to the new document
    for page_num, page in enumerate(doc):
        new_page = new_doc[page_num]
        if page_num in image_info:
            for xref, rect in image_info[page_num]:
                new_page.show_pdf_page(rect, doc, page_num, clip=rect, keep_proportion=True, overlay=True)

    new_doc.save(output_pdf)
    doc.close()
    new_doc.close()

#-----------------------------------------------------------------------------
#image info

def extract_image_info(pdf_path):
    doc = fitz.open(pdf_path)
    image_info = {}
    for page_num, page in enumerate(doc):
        image_info[page_num] = []
        for img in page.get_images(full=True):
            xref = img[0]  # xref is the reference number for the image
            img_rect = page.get_image_rects(xref)
            if img_rect:
                image_info[page_num].append((xref, img_rect[0]))  # Store xref and the first bounding rect (if multiple, consider how to handle)
    doc.close()
    return image_info


#---------------------------
#tab extraction

def extract_tabs(input_pdf):
    doc = fitz.open(input_pdf)
    tabs_not_sorted = []  # detect the tables

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        
        # Use PyMuPDF's method to extract tables
        tables = page.find_tables()

        for table in tables:
            tabs_not_sorted.append((table, page_num))
    
    tabs = real_tabs(input_pdf, tabs_not_sorted)
    cells_info = {} #We do it for every cell, no need to differentiate the tabs anymore
    for x, table in enumerate(tabs):  # iterate over all tables
        tab = table[0]
        cells_info[page_num] = []
        print(f"Table {x} column names: {tab.header.names}, external: {tab.header.external}")
        for j in range(tab.col_count):
            for i in range(tab.row_count):
                cells = fitz.make_table(tab.bbox, cols=tab.col_count, rows=tab.row_count)
                spans = page.get_text("dict", clip=cells[i][j])["blocks"][0]["lines"][0]["spans"]
                span = spans[0]
                is_title = False
                tab_values = [True, tab.row_count, tab.col_count, x, tab.bbox]
                text = span['text']
                x0, y0 = span['bbox'][:2]
                font_name = span['font']
                font_size = span['size']
                if font_size >= 14:
                    is_title = True
                flags = flags_decomposer(span["flags"])
                if 'bold' in flags and 'italic' in flags:
                    base_font = 'hebi'
                elif 'bold' in flags:
                    base_font = 'hebo'
                elif 'italic' in flags:
                    base_font = 'heit'
                else:
                    base_font = 'helv'
                color = fitz.sRGB_to_rgb(span["color"])
                color = tuple(c / 255 for c in color)
                #We need to shift by 1 on y to fit inside the table
                height_col = cells[i][j][3] - cells[i][j][1]
                pos = (x0, y0 + height_col)
                text_info = [(text, pos, base_font, font_size, color, is_title, tab_values)]
                cells_info[page_num].append((text.strip(), text_info)) #double parenthesis bc there are several block info outside the tabs
        page.draw_rect(tab.bbox, color=(1, 1, 1), fill=(1, 1, 1))
        page.add_redact_annot(tab.bbox)

    page.apply_redactions()
    doc.save(input_pdf, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    doc.close()

    return cells_info

def real_tabs(input_pdf, tabs_not_sorted):
    # Read PDF into a list of DataFrames
    tables = tabula.read_pdf(input_pdf, stream=True, pages='all', pandas_options={'header': None})
    tabs_sorted = []
    for i, table in enumerate(tables):
        for j, (potential, page_num) in enumerate(tabs_not_sorted):
            if compare_tables(table, potential):
                tabs_sorted.append((potential, page_num))

    return tabs_sorted


def compare_tables(tabula_table, pymupdf_table):

    if len(tabula_table) != pymupdf_table.row_count:
        return False

    for i in range(len(tabula_table)):
        for j in range(len(tabula_table.iloc[0])):
            if str(tabula_table.iloc[i][j]) != pymupdf_table.extract()[i][j]:
                return False

    return True

#-----------------------------------
#tab contruction

#-----------------------------------------------------------------------------
#main

input_pdf_path = "/Users/Admin/Documents/Infosys/Projects/PDF_translation/PDF.pdf"
output_pdf_path = "PDF tests copy.pdf"

# Extracting images
image_info = extract_image_info(input_pdf_path)

# Extract tabs, and hide them from extract_text
tabs_info = extract_tabs(input_pdf_path)

# Extract text and positions
text_blocks = extract_text_with_positions(input_pdf_path, tabs_info)

# Translate text
translated_blocks = {}
for page_num, blocks in text_blocks.items(): #blocks = (combined_text.strip(), block_info)
    translated_blocks[page_num] = translate_text(blocks)

# Create new PDF with translated text
create_translated_pdf(input_pdf_path, output_pdf_path, image_info, tabs_info, translated_blocks)

print(f"Translated PDF saved as: {output_pdf_path}")
