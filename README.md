# PDF Translation Automation Project


![image](https://github.com/user-attachments/assets/2bba6c90-abbc-4ae4-840d-5d9a6b1ca990)


## Overview

This project automates the process of extracting text and tables from a PDF, translating the text to French, and creating a new PDF with the translated content while maintaining the layout, including images and tables. The goal is to create an easy-to-use pipeline for translating documents without losing any formatting.

Features

	•	PDF Text Extraction: Extracts text from the PDF along with its position and formatting details.
	•	Table Detection and Processing: Detects tables in the PDF and processes them separately to preserve their structure.
	•	Text Translation: Uses a pre-trained transformer model to translate extracted English text into French.
	•	PDF Creation: Generates a new PDF with translated text, while retaining images, tables, and original formatting.

Project Structure

	•	pdf_extraction.py: Contains the logic to extract text, images, and formatting information from a PDF.
	•	tab_extraction.py: Detects and extracts tables from the PDF for further processing.
	•	translation.py: Translates the extracted text using a transformer model.
	•	create_pdf.py: Recreates a new PDF with the translated text and original layout.
	•	main.py: The main script that brings all the modules together and runs the PDF translation process.

Requirements

	•	Python 3.7+
	•	Dependencies:
	•	PyMuPDF (fitz) for PDF handling and text extraction
	•	Tabula for table extraction
	•	Transformers from HuggingFace for translation
	•	OpenCV for image handling# PDF-translator

 How to Use

	1.	Place the input PDF you want to translate in the project directory.
	2.	Set the input_pdf_path and output_pdf_path in main.py to the desired input and output file paths.
	3.	Run the main.py script

 The script will:

	•	Extract text, images, and tables from the input PDF.
	•	Translate the extracted text into French.
	•	Create a new PDF with the translated text, original images, and table structure.

The output PDF will be saved at the path specified in output_pdf_path.

Run the script and the translated PDF will be saved as translated_document.pdf.

Future Improvements

	•	Add support for more languages.
	•	Improve table translation and formatting retention.
	•	Enhance error handling for complex PDF structures.
