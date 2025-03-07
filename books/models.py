from django.db import models
from django.shortcuts import render
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.urls import reverse
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
    
    
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField()  # Duration in days

    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], default='active')

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    uploader_earning = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    platform_earning = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        """Automatically calculate earnings before saving"""
        if not self.uploader_earning or not self.platform_earning:
            uploader_percentage = self.book.user.profile.royalty_percentage / 100  # Get royalty percentage from the uploader's profile
            self.uploader_earning = self.price * uploader_percentage
            self.platform_earning = self.price * (1 - uploader_percentage)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.id} - {self.book.title} by {self.user.email}"


class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(
        max_length=20,
        choices=[('paystack', 'Paystack'), ('credit_card', 'Credit Card'), ('paypal', 'PayPal')]
    )
    status = models.CharField(
        max_length=20, 
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], 
        default='pending'
    )
    transaction_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.transaction_id} by {self.user.email}"

    

class Royalty(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='royalties')
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name='royalties')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    withdrawn = models.BooleanField(default=False)  # Track if the royalty is withdrawn
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} earned {self.amount} from {self.book.title}"
    
    

class WithdrawalRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='withdrawals')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Withdrawal of {self.amount} by {self.user.email} - {self.status}"
    
    


from django.db import transaction, models
from django.utils import timezone

class RoyaltyManager:
    @staticmethod
    def get_total_royalties(user):
        """Returns total available royalties that haven't been withdrawn."""
        return Royalty.objects.filter(user=user, withdrawn=False).aggregate(total=models.Sum('amount'))['total'] or 0

    @staticmethod
    def request_withdrawal(user, amount):
        """Creates a withdrawal request if the user has enough balance."""
        available_balance = RoyaltyManager.get_total_royalties(user)
        
        if amount > available_balance:
            raise ValueError("Insufficient balance for withdrawal request.")

        with transaction.atomic():
            # Create a new withdrawal request
            withdrawal = WithdrawalRequest.objects.create(user=user, amount=amount)

            # Mark royalties as withdrawn (only the amount requested)
            remaining_amount = amount
            royalties = Royalty.objects.filter(user=user, withdrawn=False).order_by('created_at')
            
            for royalty in royalties:
                if remaining_amount <= 0:
                    break
                if royalty.amount <= remaining_amount:
                    royalty.withdrawn = True
                    remaining_amount -= royalty.amount
                else:
                    # Split the royalty if the remaining amount is less than the royalty amount
                    new_royalty = Royalty.objects.create(
                        user=user,
                        book=royalty.book,
                        amount=royalty.amount - remaining_amount,
                        withdrawn=False
                    )
                    royalty.amount = remaining_amount
                    royalty.withdrawn = True
                    remaining_amount = 0
                royalty.save()

        return withdrawal

class Download(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='downloads')
    book = models.ForeignKey('Book', on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    download_token = models.UUIDField(default=uuid.uuid4, unique=True)  # Unique identifier for secure download link

    def __str__(self):
        return f"{self.user.email} downloaded {self.book.title}"

    def get_download_url(self):
        """Generate a secure download link using the unique token."""
        return reverse('books:download_book', kwargs={'token': str(self.download_token)})


@receiver(post_save, sender=Payment)
def handle_payment_completion(sender, instance, **kwargs):
    """Automatically populate Download and Royalty models when payment is completed."""
    if instance.status == 'completed':
        order = instance.order

        # Create or get the Download entry
        download, created = Download.objects.get_or_create(user=order.user, book=order.book)

        # Generate the download URL using SITE_URL instead of request
        download_url = f"{settings.SITE_URL}{download.get_download_url()}"

        # Calculate and record the uploader's royalty
        uploader = order.book.user
        royalty_amount = order.uploader_earning
        Royalty.objects.create(user=uploader, book=order.book, amount=royalty_amount)

        # Send download link via email
        send_mail(
            subject="Your Book Download Link",
            message=f"Hello {order.user.email},\n\nYour payment was successful! "
                    f"Click the link below to download your book:\n{download_url}\n\nEnjoy your reading!",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[order.user.email],
            fail_silently=True,
        )