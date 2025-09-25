from django.db import models
from django.shortcuts import render
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.urls import reverse
from django.core.cache import cache
from django.utils.crypto import get_random_string
from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone
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
    slug = models.SlugField(max_length=200, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            if not base_slug:  # Handle empty slugs
                base_slug = "booktype"
            
            self.slug = base_slug
            counter = 1
            # Check for duplicates excluding current instance
            while BookType.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                if counter > 100:  # Safety check
                    self.slug = f"{base_slug}-{get_random_string(4).lower()}"
                    break
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    book_type = models.ForeignKey(BookType, on_delete=models.CASCADE, related_name="categories")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
     
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            if not base_slug:  # Handle empty slugs
                base_slug = "category"
            
            self.slug = base_slug
            counter = 1
            # Check for duplicates excluding current instance
            while Category.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                if counter > 100:  # Safety check
                    self.slug = f"{base_slug}-{get_random_string(4).lower()}"
                    break
        super().save(*args, **kwargs)
        
    class Meta:
        unique_together = ('name', 'book_type')

    def __str__(self):
        return self.name

class Book(models.Model):
    cover_image = models.ImageField(upload_to='book_covers', blank=True, null=True)
    title = models.CharField(max_length=5000)
    description = models.TextField()
    book_type = models.ForeignKey(BookType, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='book')
    file = models.FileField(upload_to='book_files/', max_length=1000, blank=True, null=True)
    preview_url = models.URLField(blank=True, null=True)
    author = models.CharField(max_length=50)
    slug = models.SlugField(max_length=2000, unique=True, blank=True)
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

        try:
            # Get file extension
            file_ext = os.path.splitext(self.file.name)[1].lower()

            # Connect to GCS
            client = storage.Client(credentials=settings.GS_CREDENTIALS)
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            blob = bucket.blob(self.file.name)

            # Download file to temp path
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
                blob.download_to_filename(temp_file.name)
                file_path = temp_file.name

            # Process file
            if file_ext == ".pdf":
                return self._extract_pdf_stats(file_path)

            elif file_ext == ".docx":
                pdf_path = convert_docx_to_pdf(file_path)
                if pdf_path:
                    return self._extract_pdf_stats(pdf_path)
                else:
                    return {"pages": "Conversion failed", "words": "Conversion failed"}

            else:
                return {"pages": "Unsupported format", "words": "Unsupported format"}

        except Exception as e:
            logger.error(f"Error extracting stats: {e}")
            return {"pages": f"Error: {e}", "words": f"Error: {e}"}

        finally:
            # Always clean up the downloaded file
            if os.path.exists(file_path):
                os.remove(file_path)

    def _extract_pdf_stats(self, file_path):
        """Extracts page count and word count from a PDF."""
        with fitz.open(file_path) as pdf:
            text = " ".join(page.get_text("text") for page in pdf)
            page_count = pdf.page_count
            word_count = len(text.split())

        return {"pages": page_count, "words": word_count}
    
    def save(self, *args, **kwargs):
        file_changed = 'file' in kwargs.get('update_fields', []) or not self.pk
        
        # Generate slug if not exists
        if not self.slug:
            base_slug = slugify(self.title)
            if not base_slug:  # Handle empty slugs
                base_slug = "book"
            
            self.slug = base_slug
            counter = 1
            # Check for duplicates excluding current instance
            while Book.objects.filter(slug=self.slug).exclude(id=self.id).exists():
                self.slug = f"{base_slug}-{counter}"
                counter += 1
                if counter > 100:  # Safety check
                    self.slug = f"{base_slug}-{get_random_string(6).lower()}"
                    break
        
        super().save(*args, **kwargs)
        
        if self.file and (file_changed or not self.preview_url):
            try:
                from .utils import generate_preview
                self.preview_url = generate_preview(self)
                super().save(update_fields=['preview_url'])
            except Exception as e:
                logger.error(f"Failed to generate preview for book {self.id}: {e}")
                
                


class HireWriterRequest(models.Model):
    # Service choices
    SERVICE_CHOICES = [
        ('Project/thesis writer', 'Project/thesis writer'),
        ('Data analysis', 'Data analysis'),
        ('Questionnaire', 'Questionnaire'),
        ('Assignment', 'Assignment'),
        ('Serminal', 'Serminal'),
        ('Hire Developer', 'Hire Developer'),
        ('General', 'General (if the service not included)'),
    ]
    
    # Required fields
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    service = models.CharField(max_length=50, choices=SERVICE_CHOICES)
    name = models.CharField(max_length=100)
    email = models.EmailField(validators=[EmailValidator()])
    topic = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    description = models.TextField()
    
    # Optional field
    upload_format = models.FileField(upload_to='writer_requests/%Y/%m/%d/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Status tracking
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('reviewing', 'Reviewing'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    
    class Meta:
        verbose_name = "Hire Writer Request"
        verbose_name_plural = "Hire Writer Requests"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.service