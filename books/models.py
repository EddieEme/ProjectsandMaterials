from google.cloud import storage
from django.db import models
from django.conf import settings
import fitz  # PyMuPDF for PDFs
import os
from docx import Document 
from reportlab.pdfgen import canvas
import tempfile

class BookType(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class Book(models.Model):
    cover_image = models.ImageField(upload_to='book_covers', blank=True, null=True)
    title = models.CharField(max_length=225)
    description = models.TextField()
    book_type = models.ForeignKey(BookType, on_delete=models.SET_NULL, null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    file = models.FileField(upload_to='book_files/', blank=True, null=True)
    author = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    def get_file_statistics(self):
        """Returns page count and word count of the book's file, ensuring fresh updates."""
        if not self.file:
            return {"pages": "No file uploaded", "words": "No file uploaded"}

        # Initialize GCS client
        client = storage.Client(credentials=settings.GS_CREDENTIALS)
        bucket = client.bucket(settings.GS_BUCKET_NAME)
        blob = bucket.blob(self.file.name)  # self.file.name is the file path in GCS

        # Download the file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            blob.download_to_filename(temp_file.name)
            file_path = temp_file.name

        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == ".pdf":
                with fitz.open(file_path) as pdf:
                    text = ""
                    for page in pdf:
                        text += page.get_text("text")  # Extract text from each page

                    page_count = pdf.page_count
                    word_count = len(text.split())  # Count words

                return {"pages": page_count, "words": word_count}

            elif file_extension == ".docx":
                doc = Document(file_path)
                paragraphs = doc.paragraphs
                text = " ".join([p.text for p in paragraphs])  # Combine paragraph text

                estimated_pages = max(1, len(paragraphs) // 30)  # Estimate based on ~30 paragraphs per page
                word_count = len(text.split())

                return {"pages": estimated_pages, "words": word_count}

            else:
                return {"pages": "Unsupported file format", "words": "Unsupported file format"}

        except Exception as e:
            return {"pages": f"Error reading file: {e}", "words": f"Error reading file: {e}"}

        finally:
            # Clean up the temporary file
            if os.path.exists(file_path):
                os.remove(file_path)