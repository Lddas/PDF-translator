from pdf_extraction import extract_text_with_positions, extract_image_info
from tab_extraction import extract_tabs
from translation import translate_text
from create_pdf import create_translated_pdf

input_pdf_path = "PDF.pdf"
output_pdf_path = "PDF_translated.pdf"

image_info = extract_image_info(input_pdf_path)
tabs_info = extract_tabs(input_pdf_path)
text_blocks = extract_text_with_positions(input_pdf_path, tabs_info)
translated_blocks = {}
for page_num, blocks in text_blocks.items():
    translated_blocks[page_num] = translate_text(blocks)

create_translated_pdf(input_pdf_path, output_pdf_path, image_info, tabs_info, translated_blocks)

print(f"Translated PDF saved as: {output_pdf_path}")
