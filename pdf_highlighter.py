# -*- coding: utf-8 -*-
import fitz  # PyMuPDF
import re
import os

# Folder paths
input_folder = os.path.expanduser("~/pytools/incoming_orders")
output_folder = os.path.expanduser("~/pytools/highlighted_orders")

# Create output folder if it doesn't exist
os.makedirs(output_folder, exist_ok=True)
# Use the filename (without extension) as the order number
order_number = os.path.splitext(os.path.basename(~/pytools/incoming_orders))[0]


def get_customer_name(text):
    """
    Extract customer name - appears in the customer info block
    Look for name that appears before street address and after the date/time
    """
    # Pattern: After PM timestamp, before street address with numbers
    # Name format: firstname lastname (can be lowercase or mixed case)
    pattern = r'PM\s*\n+([A-Za-z]+\s+[A-Za-z]+)\s*\n'
    match = re.search(pattern, text)
    if match:
        name = match.group(1).strip()
        # Make sure it's not a business name or common label
        if name.lower() not in ['customer service', 'payment method', 'united states']:
            return name
    return None

def get_customer_phone(text):
    """
    Extract customer phone - only the one near the customer info section
    Must appear after an email address to be considered customer phone
    Excludes company phone number
    """
    # Find phone numbers that appear after email addresses (simpler pattern)
    pattern = r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}.*?\n.*?(\+?1?\s*\d{3}[-.\s]?\d{3}[-.\s]?\d{4})'
    matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)
    
    if not matches:
        return []
    
    # Filter out company phone
    customer_phones = []
    for phone in matches:
        # Remove all non-digits to compare
        phone_digits = re.sub(r'\D', '', phone)
        # Skip if it's the company phone (770-354-7475)
        if phone_digits != '17703547475' and phone_digits != '7703547475':
            customer_phones.append(phone)
    
    return customer_phones
    

def get_product_names(text):
    """
    Extract product names - they appear between Order # and SKU
    Captures lines that are product titles
    """
    products = []
    # Find all product names that appear before "SKU :"
    # Products are typically on their own line before SKU
    lines = text.split('\n')
    for i, line in enumerate(lines):
        # Look for lines before SKU that aren't common labels
        if i > 0 and 'SKU' in lines[i]:
            prev_line = lines[i-1].strip()
            # Check if previous line looks like a product name (not a label or number)
            if prev_line and not re.match(r'^(Size:|Artwork:|Upload|Finishing|Price:|Payment|Processing|Pickup|Items|Total|Atlanta|card|\d+|Order)', prev_line, re.IGNORECASE):
                # Avoid capturing random text
                if len(prev_line) > 3 and len(prev_line) < 100:
                    products.append(prev_line)
    return products

def get_quantities(text):
    """
    Extract quantity numbers - appear as standalone numbers before prices
    Look for pattern: whitespace, number, whitespace, then price (like " 3 $125.00")
    Must be single or double digit
    """
    quantities = []
    # Match quantities that appear right before prices
    pattern = r'(?:^|\n)\s*(\d{1,2})\s+\$\d+\.\d{2}'
    matches = re.finditer(pattern, text, re.MULTILINE)
    for match in matches:
        qty = match.group(1)
        # Avoid highlighting if it looks like a date or other number
        if int(qty) > 0 and int(qty) <= 99:
            quantities.append(qty)
    return quantities

def get_sizes(text):
    """
    Extract size specifications - various formats
    """
    sizes = []
    
    # Format 1: "6' Tall and up to 4ft wide"
    pattern1 = r'\d+[\'\"]\s*Tall\s+and\s+up\s+to\s+\d+ft\s+wide'
    sizes.extend(re.findall(pattern1, text, re.IGNORECASE))
    
    # Format 2: "6ft" or "8ft" as standalone size
    pattern2 = r'\bPrice:\s*(\d+ft)\b'
    sizes.extend(re.findall(pattern2, text, re.IGNORECASE))
    
    # Format 3: Panel dimensions like "6ft wide by 32" tall"
    pattern3 = r'\d+ft\s+wide\s+by\s+\d+["\']?\s+tall'
    sizes.extend(re.findall(pattern3, text, re.IGNORECASE))
    
    return sizes

def is_in_header(text, match_start, match_end):
    """
    Check if text position is in the header section (before customer info)
    Header ends when we see the customer name section after the timestamp
    """
    # Find where customer section starts (after "Sep XX, 20XX, XX:XX PM")
    customer_section_pattern = r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}\s+(?:AM|PM)\s*\n'
    customer_match = re.search(customer_section_pattern, text, re.IGNORECASE)
    
    if customer_match:
        header_end = customer_match.end()
        # If our match is before the customer section, it's in the header
        return match_start < header_end
    
    return False

def is_address_or_price(text_to_check):
    """
    Check if text is an address or price that should NOT be highlighted
    """
    text_stripped = text_to_check.strip()
    
    # Skip prices in any format
    if '$' in text_stripped:
        return True
    
    # Skip if it's just a number (could be part of address or price)
    if re.match(r'^\d+$', text_stripped):
        return True
    
    # Skip street addresses (contains numbers followed by street words)
    if re.search(r'\d+\s+(?:W|E|N|S|West|East|North|South|St|Street|Ave|Avenue|Dr|Drive|Rd|Road|Blvd|Boulevard|Ln|Lane|Circle|Cir|Way|Ct|Court)', text_stripped, re.IGNORECASE):
        return True
    
    # Skip city, state patterns
    if re.search(r'\b(?:Atlanta|Georgia|California|Los Angeles|United States|Ellenwood|Stone Mountain)\b', text_stripped, re.IGNORECASE):
        return True
    
    # Skip zip codes (5 digit numbers)
    if re.match(r'^\d{5}$', text_stripped):
        return True
    
    # Skip state abbreviations
    if re.match(r'^[A-Z]{2}$', text_stripped):
        return True
    
    return False

def highlight_text_precisely(page, text_to_find, color, exclude_header=True):
    """
    Highlight specific text using word-level coordinates
    """
    if not text_to_find:
        return 0
    
    words = page.get_text("words")
    full_text = page.get_text("text")
    
    # Handle list of texts
    if isinstance(text_to_find, list):
        texts = text_to_find
    else:
        texts = [text_to_find]
    
    highlighted_count = 0
    
    for search_text in texts:
        if not search_text:
            continue
        
        # Skip addresses and prices
        if is_address_or_price(search_text):
            continue
            
        # Find the text position
        pattern = re.escape(search_text)
        matches = list(re.finditer(pattern, full_text, flags=re.IGNORECASE))
        
        for match in matches:
            start_pos = match.start()
            end_pos = match.end()
            
            # Skip if in header
            if exclude_header and is_in_header(full_text, start_pos, end_pos):
                continue
            
            current_pos = 0
            word_boxes = []
            
            for word_info in words:
                x0, y0, x1, y1, word_text = word_info[:5]
                word_start = current_pos
                word_end = current_pos + len(word_text)
                
                if not (word_end <= start_pos or word_start >= end_pos):
                    rect = fitz.Rect(x0, y0, x1, y1)
                    word_boxes.append(rect)
                
                current_pos = word_end + 1
            
            for rect in word_boxes:
                highlight = page.add_highlight_annot(rect)
                highlight.set_colors(stroke=color)
                highlight.update()
            
            if word_boxes:
                highlighted_count += 1
                print(f"  🟨 Highlighted: '{search_text.strip()}'")
    
    return highlighted_count

def add_header_overlay(page, order_number, pickup_date):
    """
    Add enlarged order number and pickup date to top right corner
    """
    if not order_number and not pickup_date:
        return
    
    # Get page width
    page_width = page.rect.width
    
    # Font settings
    font_size = 24
    text_color = (0, 0, 0)  # Black
    
    # Position from top right corner
    right_margin = 50
    top_margin = 40
    line_height = 30
    
    # Prepare text lines
    lines = []
    if order_number:
        lines.append(order_number)
    if pickup_date:
        lines.append(pickup_date)
    
    # Add each line
    y_position = top_margin
    for line in lines:
        # Simple right-aligned position (approximate)
        x_position = page_width - right_margin - (len(line) * 10)
        
        # Insert text
        page.insert_text(
            (x_position, y_position),
            line,
            fontsize=font_size,
            color=text_color
        )
        
        y_position += line_height
        
    
    print(f"  📌 Added header overlay: {', '.join(lines)}")
    

def highlight_pdf(input_pdf_path, output_pdf_path):
    """
    Process PDF and highlight specific fields
    """
    doc = fitz.open(input_pdf_path)
    total_highlights = 0
    yellow = (1, 1, 0)
    
    for page_num, page in enumerate(doc, start=1):
        print(f"\n  📄 Page {page_num}:")
        text = page.get_text("text")
        
        # 1. Customer Name
        customer_name = get_customer_name(text)
        if customer_name:
            total_highlights += highlight_text_precisely(page, customer_name, yellow)
        
        # 2. Customer Phone
        customer_phones = get_customer_phone(text)
        if customer_phones:
            total_highlights += highlight_text_precisely(page, customer_phones, yellow)
        
        # 3. Order Number
        order_match = re.search(r'Order\s*#\s*\d+', text, re.IGNORECASE)
        if order_match:
            total_highlights += highlight_text_precisely(page, order_match.group(), yellow)
        
        # 4. Pickup Date/Time
        pickup_match = re.search(r'Pick\s+up\s+\w+\s*\([^)]+\)', text, re.IGNORECASE)
        if pickup_match:
            total_highlights += highlight_text_precisely(page, pickup_match.group(), yellow)
        
        # 5. Product Names
        products = get_product_names(text)
        if products:
            total_highlights += highlight_text_precisely(page, products, yellow)
        
        # 6. Quantities
        quantities = get_quantities(text)
        if quantities:
            total_highlights += highlight_text_precisely(page, quantities, yellow)
        
        # 7. Sizes
        sizes = get_sizes(text)
        if sizes:
            total_highlights += highlight_text_precisely(page, sizes, yellow)
        
        # 8. Finishing Options
        finishing_patterns = [
            r'I need a stand or a hinge of the back[^.]*\.',
            r'I do not need a stand or a hinge on the back[^.]*\.',
            r'DO NOT NEED A STAND',
            r'need a stand',
            r'FULL Arch Top',
            r'Half Arch to the (?:Left|Right)',
        ]
        
        for pattern in finishing_patterns:
            finishing_matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in finishing_matches:
                total_highlights += highlight_text_precisely(page, match.group(), yellow)
            add_header_overlay(page, order_number, pickup_date)
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
