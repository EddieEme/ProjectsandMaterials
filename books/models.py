from django.db import models
from django.shortcuts import render
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.urls import reverse
from django.core.cache import cache
import os
import uuid
import tempfile

import fitz
from docx import Document

from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

import logging

logger = logging.getLogger(__name__)



class BookType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    book_type = models.ForeignKey(BookType, on_delete=models.CASCADE, related_name="categories")

    def __str__(self):
        return self.name


class Book(models.Model):
    cover_image = models.ImageField(upload_to='book_covers', blank=True, null=True)
    title = models.CharField(max_length=225)
    description = models.TextField()
    book_type = models.ForeignKey(BookType, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    file = models.FileField(upload_to='book_files/', blank=True, null=True)
    author = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=5000)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_file_statistics(self):
        """Returns page count and word count of the file, ensuring fresh updates."""
        from .utils import convert_docx_to_pdf
        
        if not self.file:
            logger.warning("No file uploaded for book: %s", self.title)
            return {"pages": "No file uploaded", "words": "No file uploaded"}

        # Initialize GCS client
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(self.file.name)  # self.file.name is the file path in GCS

        # Download the file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(self.file.name)[1]) as temp_file:
            blob.download_to_filename(temp_file.name)
            file_path = temp_file.name

        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == ".pdf":
                logger.info("Processing PDF file: %s", file_path)
                return self._extract_pdf_stats(file_path)

            elif file_extension == ".docx":
                logger.info("Processing DOCX file: %s", file_path)
                pdf_path = convert_docx_to_pdf(file_path)
                if pdf_path:
                    logger.info("DOCX to PDF conversion successful: %s", pdf_path)
                    return self._extract_pdf_stats(pdf_path)
                else:
                    logger.error("DOCX to PDF conversion failed for file: %s", file_path)
                    return {"pages": "Conversion failed", "words": "Conversion failed"}

            else:
                logger.warning("Unsupported file format: %s", file_extension)
                return {"pages": "Unsupported file format", "words": "Unsupported file format"}

        except Exception as e:
            logger.error("Error processing file: %s", e)
            return {"pages": f"Error reading file: {e}", "words": f"Error reading file: {e}"}

        finally:
            # Clean up temporary files
            if os.path.exists(file_path):
                logger.info("Cleaning up temporary file: %s", file_path)
                os.remove(file_path)

    def _extract_pdf_stats(self, file_path):
        """Extracts page count and word count from a PDF."""
        with fitz.open(file_path) as pdf:
            text = " ".join(page.get_text("text") for page in pdf)
            page_count = pdf.page_count
            word_count = len(text.split())

        return {"pages": page_count, "words": word_count}