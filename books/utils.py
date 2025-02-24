import os
import fitz
from django.shortcuts import get_object_or_404, render
from docx import Document
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import simpleSplit
from django.conf import settings
from django.http import FileResponse, HttpResponseNotFound
from .models import Book

def extract_first_10_pages(book):
    """Generates a preview PDF with the first 10 pages of a book."""
    if not book.file:
        return None
    
    file_path = book.file.path
    file_extension = os.path.splitext(file_path)[1].lower()

    # Ensure preview directory exists
    preview_dir = os.path.join(settings.MEDIA_ROOT, "previews")
    os.makedirs(preview_dir, exist_ok=True)

    # Define preview file path
    preview_path = os.path.join(preview_dir, f"preview_{book.id}.pdf")

    try:
        if file_extension == ".pdf":
            # Extract first 10 pages from PDF
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
            # Convert first 10 pages of DOCX to PDF
            doc = Document(file_path)
            new_pdf = canvas.Canvas(preview_path, pagesize=letter)
            width, height = letter
            y_position = height - 50  # Start near the top

            try:
                for para in doc.paragraphs:
                    text = para.text.strip()
                    if text:
                        lines = simpleSplit(text, "Helvetica", 12, width - 100)  # Word wrap
                        for line in lines:
                            new_pdf.drawString(50, y_position, line)
                            y_position -= 20
                            if y_position < 50:  # Move to next page when needed
                                new_pdf.showPage()
                                y_position = height - 50
                new_pdf.save()
            finally:
                new_pdf.showPage()
                new_pdf.save()

        return f"/media/previews/preview_{book.id}.pdf"  # Relative URL for frontend use

    except Exception as e:
        print(f"Error generating preview: {e}")
        return None

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

