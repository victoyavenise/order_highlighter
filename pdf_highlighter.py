# -*- coding: utf-8 -*-
import fitz  # PyMuPDF
import re
import os

# Folder paths
input_folder = os.path.expanduser("~/pytools/incoming_orders")
output_folder = os.path.expanduser("~/pytools/highlighted_orders")

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)

# Color coding for different field types (RGB values 0-1)
COLORS = {
    "Name": (1, 1, 0),          # Yellow
    "Phone": (1, 1, 0),          # Yellow
    "Order": (1, 1, 0),          # Yellow
    "Pickup": (1, 1, 0),         # Yellow
    "Size": (1, 1, 0),           # Yellow
    "Product": (1, 1, 0),        # Yellow
    "Finishing": (1, 1, 0),      # Yellow
}

# Patterns for each field type based on your PDF
PATTERNS = {
    # Customer name (appears near top)
    "Name": r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",
    
    # Phone number
    "Phone": r"\+?1?\s*\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})",
    
    # Order number
    "Order": r"Order\s*#?\s*\d+",
    
    # Pickup date/time
    "Pickup": r"Pick\s+up\s+\w+\s*\([^)]+\)",
    
    # Size specifications
    "Size": r"\d+['\"]?\s*Tall\s+and\s+up\s+to\s+\d+ft\s+wide",
    
    # Product types
    "Product": r"(?:Standee\*?|Arches\s*\([^)]+\))",
    
    # Finishing options (need/don't need stand, arch directions)
    "Finishing": r"(?:DO NOT NEED A STAND|need a stand|I need a stand or a hinge|I do not need a stand|FULL Arch Top|Half Arch to the Left|Half Arch to the Right)",
}

def highlight_text_precisely(page, pattern, color, label):
    """
    Highlight text using word-level coordinates for precision
    """
    # Get text with word-level details
    words = page.get_text("words")
    
    # Get full page text for regex matching
    full_text = page.get_text("text")
    
    # Find all matches in the text
    matches = list(re.finditer(pattern, full_text, flags=re.IGNORECASE))
    
    highlighted_count = 0
    
    for match in matches:
        matched_text = match.group()
        start_pos = match.start()
        end_pos = match.end()
        
        # Build the text position map from words
        current_pos = 0
        word_boxes = []
        
        # Reconstruct text position from words to find which words are in our match
        for word_info in words:
            x0, y0, x1, y1, word_text = word_info[:5]
            word_start = current_pos
            word_end = current_pos + len(word_text)
            
            # Check if this word overlaps with our match
            if not (word_end <= start_pos or word_start >= end_pos):
                # This word is part of the match
                rect = fitz.Rect(x0, y0, x1, y1)
                word_boxes.append(rect)
            
            current_pos = word_end + 1  # +1 for space between words
        
        # Highlight all words in the match
        for rect in word_boxes:
            highlight = page.add_highlight_annot(rect)
            highlight.set_colors(stroke=color)
            highlight.update()
        
        if word_boxes:
            highlighted_count += 1
            print(f"  🟨 {label}: '{matched_text.strip()}'")
    
    return highlighted_count

def highlight_pdf(input_pdf_path, output_pdf_path):
    """
    Process PDF and highlight all matching patterns
    """
    doc = fitz.open(input_pdf_path)
    total_highlights = 0
    
    for page_num, page in enumerate(doc, start=1):
        print(f"\n  📄 Page {page_num}:")
        
        for label, pattern in PATTERNS.items():
            color = COLORS.get(label, (1, 1, 0))
            count = highlight_text_precisely(page, pattern, color, label)
            total_highlights += count
    
    # Save with compression
    doc.save(output_pdf_path, garbage=4, deflate=True, clean=True)
    doc.close()
    
    print(f"\n✅ Total highlights: {total_highlights}")
    print(f"✅ Saved: {output_pdf_path}\n")

# Process all PDFs in the input folder
print("🚀 Starting PDF highlighting process...\n")

pdf_count = 0
for filename in os.listdir(input_folder):
    if filename.lower().endswith(".pdf"):
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, f"highlighted_{filename}")
        
        print(f"{'='*60}")
        print(f"📋 Processing: {filename}")
        print(f"{'='*60}")
        
        try:
            highlight_pdf(input_path, output_path)
            pdf_count += 1
        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}\n")

print(f"{'='*60}")
print(f"✅ Complete! Processed {pdf_count} PDF(s)")
print(f"{'='*60}")
