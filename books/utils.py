import os
import fitz  # PyMuPDF
from django.shortcuts import get_object_or_404, redirect
from django.http import FileResponse, HttpResponseNotFound
from django.views.decorators.cache import never_cache
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
from celery import shared_task

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

    
@shared_task(bind=True)
def generate_preview_task(self, book_id):
    try:
        book = Book.objects.get(id=book_id)
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        preview_bucket = client.bucket("preview_projectandmaterials")
        
        preview_filename = f"previews/{book.id}/preview.pdf"
        preview_blob = preview_bucket.blob(preview_filename)
        
        if preview_blob.exists():
            url = f"https://storage.googleapis.com/preview_projectandmaterials/{preview_filename}"
            book.preview_url = url
            book.save(update_fields=['preview_url'])
            return url

        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(book.file.name)[1]) as temp_input, \
             tempfile.NamedTemporaryFile(suffix=".pdf") as temp_output:
            
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(book.file.name)
            blob.download_to_filename(temp_input.name)
            
            file_ext = os.path.splitext(temp_input.name)[1].lower()
            if file_ext == '.pdf':
                pdf_path = temp_input.name
            elif file_ext in ('.doc', '.docx'):
                pdf_path = convert_docx_to_pdf(temp_input.name)
                if not pdf_path:
                    return None
            else:
                return None

            with fitz.open(pdf_path) as doc, fitz.open() as new_doc:
                new_doc.insert_pdf(doc, to_page=min(9, len(doc)-1))
                new_doc.save(temp_output.name)

            preview_blob.upload_from_filename(
                temp_output.name,
                content_type="application/pdf",
                predefined_acl="publicRead"
            )

        url = f"https://storage.googleapis.com/preview_projectandmaterials/{preview_filename}"
        book.preview_url = url
        book.save(update_fields=['preview_url'])
        return url

    except Exception as e:
        logger.error(f"Error in generate_preview_task for book {book_id}: {e}")
        return None

@never_cache
def serve_preview(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    
    if not book.preview_url:
        return HttpResponseNotFound("Preview not yet generated")
    
    try:
        # Extract the path from the GCS URL
        gcs_path = book.preview_url.replace("https://storage.googleapis.com/preview_projectandmaterials/", "")
        
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket("preview_projectandmaterials")
        blob = bucket.blob(gcs_path)
        
        if not blob.exists():
            return HttpResponseNotFound("Preview file missing")
            
        # Create a streaming response
        file = blob.open('rb')
        response = FileResponse(file, content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{book.slug}_preview.pdf"'
        return response
        
    except Exception as e:
        logger.error(f"Error serving preview for book {book_id}: {e}")
        return HttpResponseNotFound("Error serving preview")


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
