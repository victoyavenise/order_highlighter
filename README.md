# order_highlighter

Automatically highlights key fields in order PDFs.

## What it highlights (all in yellow):
- Customer names
- Phone numbers
- Order numbers
- Pickup dates
- Product sizes
- Product types (Standee, Arches, etc.)
- Finishing options

## Setup

1. Install PyMuPDF:
```bash
   pip3 install PyMuPDF

   Place PDFs in incoming_orders/ folder

2. Run the script:

3. bash   python3 pdf_highlighter.py

4. Check highlighted_orders/ for results

Folder Structure
pytools/
├── pdf_highlighter.py
├── incoming_orders/     (input PDFs go here)
└── highlighted_orders/  (output PDFs appear here)