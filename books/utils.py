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
    """
    Serve the preview PDF inline instead of forcing a download.
    Uses StreamingHttpResponse to ensure proper file handling.
    """
    try:
        book = get_object_or_404(Book, id=book_id)
        
        # Define the preview file path
        preview_filename = f"preview_{book_id}.pdf"
        preview_path = os.path.join(settings.MEDIA_ROOT, "previews", preview_filename)
        
        logger.info(f"Looking for preview at: {preview_path}")
        
        # Check if preview exists
        if not os.path.exists(preview_path):
            logger.info(f"Preview not found for book {book_id}, attempting to generate it")
            
            # Try to generate preview if it doesn't exist
            preview_url = extract_first_10_pages(book)
            if not preview_url:
                logger.error(f"Could not generate preview for book {book_id}")
                return HttpResponseNotFound("Preview could not be generated.")
            
            # Re-check if the file exists now
            if not os.path.exists(preview_path):
                logger.error(f"Preview file not found at {preview_path} after generation")
                return HttpResponseNotFound("Preview generation failed.")
            
            logger.info(f"Preview generated successfully at {preview_path}")
        
        # Use FileResponse with safe file handling
        response = FileResponse(
            open(preview_path, "rb"),
            content_type="application/pdf",
            as_attachment=False,
            filename=f"preview_{book_id}.pdf"
        )
        
        # FileResponse automatically sets Content-Disposition, but we can override if needed
        # Setting inline ensures browser attempts to display the PDF
        response["Content-Disposition"] = f"inline; filename=preview_{book_id}.pdf"
        
        # Important: Let FileResponse manage the file - don't close it manually
        # The file will be automatically closed when the response is processed
        return response
            
    except Exception as e:
        logger.error(f"Error serving preview for book {book_id}: {str(e)}")
        return HttpResponseNotFound(f"Error serving preview: {str(e)}")

# Updated extract_first_10_pages function with consistent path usage
def extract_first_10_pages(book):
    """
    Generates a preview PDF with the first 10 pages of a book.
    Returns the relative URL path to the preview file or None if generation failed.
    """
    if not book.file:
        logger.warning(f"Cannot generate preview for book {book.id}: No file attached")
        return None

    # Ensure GCS settings exist
    if not hasattr(settings, 'GS_CREDENTIALS') or not hasattr(settings, 'GS_BUCKET_NAME'):
        logger.error("GCS settings missing: GS_CREDENTIALS or GS_BUCKET_NAME not configured")
        return None

    temp_file_path = None
    converted_pdf_path = None
    preview_path = None

    try:
        preview_dir = os.path.join(settings.MEDIA_ROOT, "previews")
        os.makedirs(preview_dir, exist_ok=True)

        preview_filename = f"preview_{book.id}.pdf"
        preview_path = os.path.join(preview_dir, preview_filename)
        preview_url = f"/media/previews/{preview_filename}"

        logger.info(f"Generating preview for book {book.id}")

        # Download the file from GCS
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(book.file.name)

        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(book.file.name)[1]) as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_file_path = temp_file.name

        logger.info(f"Downloaded file from GCS to {temp_file_path}")

        # Determine file extension
        file_extension = os.path.splitext(temp_file_path)[1].lower()

        # Remove existing preview if it exists
        if os.path.exists(preview_path):
            os.remove(preview_path)

        if file_extension == ".pdf":
            logger.info(f"Processing PDF file for book {book.id}")
            with fitz.open(temp_file_path) as doc, fitz.open() as new_doc:
                for page_num in range(min(10, len(doc))):
                    new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                new_doc.save(preview_path)
                logger.info(f"Saved PDF preview with {min(10, len(doc))} pages")

        elif file_extension in [".docx", ".doc"]:
            logger.info(f"Processing DOCX file for book {book.id}")
            converted_pdf_path = convert_docx_to_pdf(temp_file_path)
            if not converted_pdf_path:
                logger.error(f"Failed to convert DOCX to PDF for book {book.id}")
                return None

            logger.info(f"Successfully converted DOCX to PDF: {converted_pdf_path}")

            # Now extract first 10 pages from the converted PDF
            try:
                with fitz.open(converted_pdf_path) as doc, fitz.open() as new_doc:
                    for page_num in range(min(10, len(doc))):
                        new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
                    new_doc.save(preview_path)
                    logger.info(f"Saved DOCX preview with {min(10, len(doc))} pages")
            except Exception as e:
                logger.error(f"Error extracting pages from converted PDF: {str(e)}")
                import shutil
                shutil.copy(converted_pdf_path, preview_path)
                logger.warning(f"Using full PDF as preview due to extraction error")
        else:
            logger.warning(f"Unsupported file format for preview: {file_extension}")
            return None

        # Verify the preview file exists
        if os.path.exists(preview_path):
            logger.info(f"Preview successfully created at {preview_path}")
            return preview_url
        else:
            logger.error("Preview file was not created.")
            return None

    except Exception as e:
        logger.error(f"Error generating preview for book {book.id}: {str(e)}")
        return None

    finally:
        # Clean up temporary files
        for path in [temp_file_path, converted_pdf_path]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                    logger.info(f"Removed temporary file: {path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file {path}: {str(e)}")


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