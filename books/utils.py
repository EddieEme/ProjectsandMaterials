import os
import fitz  # PyMuPDF
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, HttpResponseNotFound
from docx import Document
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from django.conf import settings
from .models import Book
from payments.models import Download
from google.cloud import storage
import subprocess
import tempfile
import requests
from django.conf import settings
import datetime
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

class Paystack:
    base_url = "https://api.paystack.co"

    @staticmethod
    def verify_payment(reference):
        """Verify transaction from Paystack."""
        url = f"{Paystack.base_url}/transaction/verify/{reference}"
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        response = requests.get(url, headers=headers)
        return response.json()




# def convert_docx_to_pdf(docx_path, pdf_path):
#     """Converts a .docx file (paragraphs & tables) to PDF (Linux-friendly)."""
#     doc = Document(docx_path)
#     pdf_canvas = canvas.Canvas(pdf_path, pagesize=letter)
    
#     width, height = letter
#     y_position = height - 50  # Start position

#     def add_text(text):
#         """Helper function to add text to PDF."""
#         nonlocal y_position
#         pdf_canvas.drawString(50, y_position, text)
#         y_position -= 20  # Move down for the next line
#         if y_position < 50:  # Create a new page if needed
#             pdf_canvas.showPage()
#             y_position = height - 50

#     # Extract paragraphs
#     for para in doc.paragraphs:
#         text = para.text.strip()
#         if text:
#             add_text(text)

#     # Extract tables
#     for table in doc.tables:
#         for row in table.rows:
#             row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
#             if row_text:
#                 add_text(row_text)

#     pdf_canvas.save()


def convert_docx_to_pdf(docx_path):
    """
    Converts a DOCX file to a PDF using `unoconv`.
    Returns the PDF file path.
    """
    if not os.path.exists(docx_path):
        raise FileNotFoundError(f"File not found: {docx_path}")

    pdf_path = docx_path.replace(".docx", ".pdf")

    try:
        # Run unoconv command
        subprocess.run(["unoconv", "-f", "pdf", "-o", pdf_path, docx_path], check=True)
        
        if not os.path.exists(pdf_path):
            raise FileNotFoundError("PDF conversion failed.")
        
        return pdf_path

    except subprocess.CalledProcessError as e:
        print(f"Error during DOCX to PDF conversion: {e}")
        return None


def serve_preview(request, book_id):
    try:
        book = get_object_or_404(Book, id=book_id)

        # Generate or reuse preview URL
        preview_url = extract_first_10_pages(book)
        if not preview_url:
            return HttpResponseNotFound("Preview not available.")

        return redirect(preview_url)  # ✅ No need for signed URL

    except Exception as e:
        logger.error(f"Error serving preview for book {book_id}: {e}")
        return HttpResponseNotFound("Error occurred while serving preview.")



def extract_first_10_pages(book):
    if not book.file:
        logger.warning(f"Cannot generate preview for book {book.id}: No file attached")
        return None

    try:
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        preview_bucket = client.bucket("preview_projectandmaterials")  # ✅ Use public bucket

        original_name = os.path.splitext(os.path.basename(book.file.name))[0]
        preview_filename = f"{original_name}_preview.pdf"
        gcs_blob_path = f"{preview_filename}"

        logger.info(f"Preparing to generate preview for: {preview_filename}")

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(book.file.name)[1]) as temp_input_file:
            bucket = client.bucket(settings.GS_BUCKET_NAME)  # Your main book bucket
            blob = bucket.blob(book.file.name)
            blob.download_to_filename(temp_input_file.name)
            temp_file_path = temp_input_file.name

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_output_file:
            preview_temp_path = temp_output_file.name

        file_extension = os.path.splitext(temp_file_path)[1].lower()

        if file_extension == ".pdf":
            with fitz.open(temp_file_path) as doc, fitz.open() as new_doc:
                for page_num in range(min(10, len(doc))):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                new_doc.save(preview_temp_path)
        elif file_extension in [".doc", ".docx"]:
            converted_pdf_path = convert_docx_to_pdf(temp_input_file.name)
            if not converted_pdf_path:
                return None
            with fitz.open(converted_pdf_path) as doc, fitz.open() as new_doc:
                for page_num in range(min(10, len(doc))):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                new_doc.save(preview_temp_path)
        else:
            return None

        preview_blob = preview_bucket.blob(gcs_blob_path)
        preview_blob.upload_from_filename(preview_temp_path, content_type="application/pdf")

        logger.info(f"Uploaded preview to public bucket at {gcs_blob_path}")

        # ✅ Public URL
        public_url = f"https://storage.googleapis.com/preview_projectandmaterials/{preview_filename}"
        return public_url

    except Exception as e:
        logger.error(f"Error generating preview for book {book.id}: {e}")
        return None

    finally:
        for path in [temp_file_path, preview_temp_path]:
            if path and os.path.exists(path):
                os.remove(path)

def download_book(request, token):
    download = get_object_or_404(Download, download_token=token)

    # Ensure the book has a file
    if not download.book.file:
        return HttpResponse("File not found", status=404)

    # ✅ Use file.url (GCS provides a public URL for stored files)
    if hasattr(download.book.file, 'url'):
        return redirect(download.book.file.url)  # ✅ Redirect to GCS file URL

    return HttpResponse("Download failed", status=500)

# import logging
# logger = logging.getLogger(__name__)

# def generate_signed_url(bucket_name, blob_name, expiration=3600):
#     """Generate a signed URL for a GCS object."""
#     try:
#         # Use the credentials from Django settings
#         storage_client = storage.Client(credentials=settings.GS_CREDENTIALS)
#         bucket = storage_client.bucket(bucket_name)
#         blob = bucket.blob(blob_name)
        
#         # Generate a signed URL with the specified expiration time
#         url = blob.generate_signed_url(
#             expiration=timedelta(seconds=expiration),
#             version="v4"  # Use v4 signing
#         )
#         return url
#     except Exception as e:
#         logger.error(f"Error generating signed URL: {str(e)}")
#         raise

# def download_book(request, token):
#     try:
#         # Retrieve the download object
#         download = get_object_or_404(Download, download_token=token)

#         # Check if the book file exists
#         if not download.book.file:
#             logger.error(f"File not found for download token: {token}")
#             return HttpResponse("File not found", status=404)

#         # Extract the GCS file path
#         gcs_url = download.book.file.url
#         bucket_name = settings.GS_BUCKET_NAME  # Use the bucket name from settings

#         # Extract the relative file path from the GCS URL
#         if bucket_name not in gcs_url:
#             logger.error(f"Invalid GCS URL for download token: {token}")
#             return HttpResponse("Invalid GCS URL", status=400)
#         file_path = gcs_url.split(bucket_name + "/")[-1]  # Get only the relative path

#         # Generate a signed URL (valid for 1 hour)
#         signed_url = generate_signed_url(bucket_name, file_path, expiration=3600)

#         # Redirect to the signed URL for download
#         return redirect(signed_url)
#     except Exception as e:
#         logger.error(f"Error processing download request for token {token}: {str(e)}")
#         return HttpResponse("An error occurred while processing your request.", status=500)