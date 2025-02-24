from django.db import models
from django.conf import settings
import fitz  # PyMuPDF for PDFs
import os
from docx import Document 
from reportlab.pdfgen import canvas

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
        """Returns a dictionary containing the page count and word count of the book's file."""
        if not self.file:
            return {"pages": "No file uploaded", "words": "No file uploaded"}

        file_path = self.file.path
        file_extension = os.path.splitext(file_path)[1].lower()

        try:
            if file_extension == ".pdf":
                with fitz.open(file_path) as pdf:
                    text = ""
                    for page in pdf:  
                        text += page.get_text("text")  # Extract text from each page

                    page_count = pdf.page_count
                    word_count = len(text.split())  # Count words in the extracted text

                return {"pages": page_count, "words": word_count}

            elif file_extension == ".docx":
                doc = Document(file_path)
                paragraphs = doc.paragraphs
                text = " ".join([p.text for p in paragraphs])  # Combine all paragraph text

                estimated_pages = max(1, len(paragraphs) // 30)  # Estimate based on ~30 paragraphs per page
                word_count = len(text.split())  # Count words

                return {"pages": estimated_pages, "words": word_count}

            else:
                return {"pages": "Unsupported file format", "words": "Unsupported file format"}

        except Exception as e:
            return {"pages": f"Error reading file: {e}", "words": f"Error reading file: {e}"}
        
        
    # def extract_first_10_pages(self):
    #     """Creates a temporary file with the first 10 pages of the document while preserving formatting."""
    #     file_path = self.file.path
    #     file_extension = os.path.splitext(file_path)[1].lower()

    #     # Output file (Temporary)
    #     preview_folder = os.path.join(settings.MEDIA_ROOT, "previews")
    #     os.makedirs(preview_folder, exist_ok=True)  # Ensure the folder exists

    #     temp_file_path = os.path.join(preview_folder, f"preview_{self.id}.pdf")

    #     if file_extension == ".pdf":
    #         try:
    #             doc = fitz.open(file_path)
    #             new_doc = fitz.open()
    #             for page_num in range(min(10, doc.page_count)):  # Use `doc.page_count`
    #                 new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
    #             new_doc.save(temp_file_path)
    #             new_doc.close()
    #             return os.path.join(settings.MEDIA_URL, "previews", f"preview_{self.id}.pdf")
    #         except Exception as e:
    #             return f"Error processing PDF: {e}"

    #     elif file_extension == ".docx":
    #         try:
    #             doc = Document(file_path)
    #             new_pdf = canvas.Canvas(temp_file_path)
    #             paragraphs = doc.paragraphs[:300]  # Approx. 10 pages worth of text
    #             y_position = 800
    #             for para in paragraphs:
    #                 new_pdf.drawString(50, y_position, para.text)
    #                 y_position -= 20
    #                 if y_position < 50:
    #                     new_pdf.showPage()
    #                     y_position = 800
    #             new_pdf.save()
    #             return os.path.join(settings.MEDIA_URL, "previews", f"preview_{self.id}.pdf")
    #         except Exception as e:
    #             return f"Error processing DOCX: {e}"

    #     else:
    #         return "Unsupported file format."