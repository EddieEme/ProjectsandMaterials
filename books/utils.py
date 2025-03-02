import os
import fitz  # PyMuPDF
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponseNotFound
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.conf import settings
from .models import Book
from google.cloud import storage
import tempfile

def convert_docx_to_pdf(docx_path, pdf_path):
    """Converts a .docx file (paragraphs & tables) to PDF (Linux-friendly)."""
    doc = Document(docx_path)
    pdf_canvas = canvas.Canvas(pdf_path, pagesize=letter)
    
    width, height = letter
    y_position = height - 50  # Start position

    def add_text(text):
        """Helper function to add text to PDF."""
        nonlocal y_position
        pdf_canvas.drawString(50, y_position, text)
        y_position -= 20  # Move down for the next line
        if y_position < 50:  # Create a new page if needed
            pdf_canvas.showPage()
            y_position = height - 50

    # Extract paragraphs
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            add_text(text)

    # Extract tables
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                add_text(row_text)

    pdf_canvas.save()


def extract_first_10_pages(book):
    """Generates a preview PDF with the first 10 pages of a book."""
    if not book.file:
        return None

    # Initialize GCS client
    client = storage.Client(credentials=settings.GS_CREDENTIALS)
    bucket = client.bucket(settings.GS_BUCKET_NAME)
    blob = bucket.blob(book.file.name)  # book.file.name is the file path in GCS

    # Download the file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(book.file.name)[1]) as temp_file:
        blob.download_to_filename(temp_file.name)
        file_path = temp_file.name

    file_extension = os.path.splitext(file_path)[1].lower()

    # Ensure preview directory exists
    preview_dir = os.path.join(settings.MEDIA_ROOT, "previews")
    os.makedirs(preview_dir, exist_ok=True)

    # Define preview file path
    preview_path = os.path.join(preview_dir, f"preview_{book.id}.pdf")

    try:
        # Delete existing preview before generating a new one
        if os.path.exists(preview_path):
            os.remove(preview_path)

        if file_extension == ".pdf":
            doc = fitz.open(file_path)
            new_doc = fitz.open()
            try:
                for page_num in range(min(10, len(doc))):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                new_doc.save(preview_path)
            finally:
                new_doc.close()
                doc.close()

        elif file_extension == ".docx":
            # Convert .docx to PDF directly into preview_path
            convert_docx_to_pdf(file_path, preview_path)

        return f"/media/previews/preview_{book.id}.pdf" 

    except Exception as e:
        print(f"Error generating preview: {e}")
        return None

    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

def serve_preview(request, book_id):
    """Serve the preview PDF inline instead of forcing a download."""
    book = get_object_or_404(Book, id=book_id)
    preview_url = extract_first_10_pages(book)

    if preview_url:
        preview_path = os.path.join(settings.MEDIA_ROOT, "previews", f"preview_{book.id}.pdf")
        
        if os.path.exists(preview_path):
            try:
                response = FileResponse(open(preview_path, "rb"), content_type="application/pdf")
                response["Content-Disposition"] = "inline; filename=preview.pdf"  # Open inline, not download
                return response
            except Exception as e:
                print(f"Error serving preview: {e}")
                return HttpResponseNotFound("Preview not available.")
    
    return HttpResponseNotFound("Preview not available.")
