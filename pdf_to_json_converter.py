#!/usr/bin/env python3
"""
PDF to JSON Converter for Legal Documents
Converts PDF files from the wetransfer directory to structured JSON format
"""

import os
import json
import re
from pathlib import Path
import PyPDF2
import pdfplumber

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using multiple methods for better accuracy"""
    text = ""
    
    # Try pdfplumber first (better for complex layouts)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as e:
        print(f"pdfplumber failed for {pdf_path}: {e}")
        
        # Fallback to PyPDF2
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
        except Exception as e2:
            print(f"PyPDF2 also failed for {pdf_path}: {e2}")
            return None
    
    return text.strip()

def parse_legal_document(text, filename):
    """Parse legal document text into structured JSON format"""
    if not text:
        return None
    
    # Clean up the text
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = text.strip()
    
    # Try to identify document structure
    articles = []
    
    # Look for article patterns (Član, Article, etc.)
    article_patterns = [
        r'Član\s+(\d+[a-z]*)\.?\s*',
        r'Article\s+(\d+[a-z]*)\.?\s*',
        r'član\s+(\d+[a-z]*)\.?\s*',
        r'CLAN\s+(\d+[a-z]*)\.?\s*',
        r'CLAN\s+(\d+[a-z]*)\.?\s*'
    ]
    
    # Split text into potential articles
    current_article = None
    current_content = []
    
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new article
        article_found = False
        for pattern in article_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                # Save previous article if exists
                if current_article:
                    articles.append({
                        "title": f"Član {current_article}",
                        "texts": current_content,
                        "link": None
                    })
                
                # Start new article
                current_article = match.group(1)
                current_content = [line]
                article_found = True
                break
        
        if not article_found and current_article:
            current_content.append(line)
    
    # Add the last article
    if current_article:
        articles.append({
            "title": f"Član {current_article}",
            "texts": current_content,
            "link": None
        })
    
    # If no articles found, treat the entire document as one article
    if not articles:
        articles.append({
            "title": "Dokument",
            "texts": [text],
            "link": None
        })
    
    return articles

def process_pdf_directory(pdf_dir, output_dir):
    """Process all PDF files in a directory"""
    pdf_path = Path(pdf_dir)
    output_path = Path(output_dir)
    
    if not pdf_path.exists():
        print(f"PDF directory {pdf_dir} does not exist")
        return
    
    output_path.mkdir(exist_ok=True)
    
    processed_count = 0
    failed_count = 0
    
    for pdf_file in pdf_path.glob("*.pdf"):
        print(f"Processing: {pdf_file.name}")
        
        try:
            # Extract text from PDF
            text = extract_text_from_pdf(pdf_file)
            
            if not text:
                print(f"Failed to extract text from {pdf_file.name}")
                failed_count += 1
                continue
            
            # Parse the document
            articles = parse_legal_document(text, pdf_file.name)
            
            if not articles:
                print(f"Failed to parse document structure from {pdf_file.name}")
                failed_count += 1
                continue
            
            # Create output filename
            output_filename = pdf_file.stem + ".json"
            output_file = output_path / output_filename
            
            # Save as JSON
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            
            print(f"Successfully processed: {pdf_file.name} -> {output_filename}")
            processed_count += 1
            
        except Exception as e:
            print(f"Error processing {pdf_file.name}: {e}")
            failed_count += 1
    
    print(f"\nProcessing complete:")
    print(f"Successfully processed: {processed_count} files")
    print(f"Failed: {failed_count} files")

def main():
    """Main function"""
    pdf_directory = "wetransfer_35-25-lat-pdf_2025-10-19_0027"
    output_directory = "scraper/laws"
    
    print("Starting PDF to JSON conversion...")
    print(f"Input directory: {pdf_directory}")
    print(f"Output directory: {output_directory}")
    
    process_pdf_directory(pdf_directory, output_directory)

if __name__ == "__main__":
    main()
