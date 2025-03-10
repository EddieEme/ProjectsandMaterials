from django.db import models
from django.conf import settings
from django.utils import timezone


# Create your models here.
class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField()  # Duration in days
    download_limit = models.IntegerField(default=0)  # 0 means unlimited
    features = models.JSONField(default=list, blank=True)  # Store additional features as JSON

    def __str__(self):
        return self.name
    
    def get_monthly_price(self):
        """Calculate and return the monthly price equivalent for display purposes."""
        if self.duration >= 28:
            monthly_price = (self.price / self.duration) * 30
            return round(monthly_price, 2)
        return self.price


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending')
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_reference = models.CharField(max_length=255, blank=True, null=True)
    subscription_reference = models.CharField(max_length=255, blank=True, null=True)  # For recurring payments
    downloads_used = models.IntegerField(default=0)  # Track downloads used in this subscription period

    def __str__(self):
        return f"{self.user.email} - {self.plan.name}"
    
    def is_active(self):
        """Check if subscription is currently active."""
        return self.status == 'active' and self.end_date > timezone.now()
    
    def days_remaining(self):
        """Return the number of days remaining in subscription."""
        if not self.is_active():
            return 0
        
        delta = self.end_date - timezone.now()
        return max(0, delta.days)
    
    def downloads_remaining(self):
        """Return number of downloads remaining in subscription."""
        if not self.is_active():
            return 0
            
        if self.plan.download_limit == 0:  # Unlimited
            return float('inf')
            
        return max(0, self.plan.download_limit - self.downloads_used)
