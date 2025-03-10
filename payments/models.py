from django.db import models
from django.conf import settings
from books.models import Book
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.urls import reverse
import uuid
import logging


logger = logging.getLogger(__name__)



# Create your models here.
class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
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

    

class Royalty(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='royalties')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='royalties')
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
    

class Download(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='downloads')
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    downloaded_at = models.DateTimeField(auto_now_add=True)
    download_token = models.UUIDField(default=uuid.uuid4, unique=True)  # Unique identifier for secure download link

    def __str__(self):
        return f"{self.user.email} downloaded {self.book.title}"

    def get_download_url(self):
        """Generate a secure download link using the unique token."""
        return reverse('payments:download_book', kwargs={'token': str(self.download_token)})
    
    

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




