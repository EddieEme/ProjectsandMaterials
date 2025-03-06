from django.contrib import admin
from .models import Book, BookType, Category, UserSubscription, SubscriptionPlan, Order, Payment, Download, WithdrawalRequest
from django.utils import timezone

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'price', 'is_approved', 'created_at', 'user', 'updated_at')
    list_filter = ('is_approved', 'author', 'category', 'created_at')
    search_fields = ('title', 'author', 'category', 'book_type')
    actions = ['approve_books']

    def approve_books(self, request, queryset):
        queryset.update(is_approved=True)
    approve_books.short_description = "Approve selected books"
    
    
admin.site.register(BookType)
admin.site.register(Category)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date')
    list_filter = ('status', 'plan')
    search_fields = ('user__email', 'plan__name')

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration')
    search_fields = ('name', 'description')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'book', 'uploader_earning', 'platform_earning', 'created_at')
    list_filter = ('status',)
    search_fields = ('user__email',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'order', 'amount', "payment_method", 'status', 'created_at')
    list_filter = ('status', 'payment_method')
    search_fields = ('user__email', 'transaction_id')

@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'downloaded_at')
    search_fields = ('user__email', 'book__title')
    


class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'created_at', 'processed_at')
    actions = ['approve_withdrawal', 'reject_withdrawal']

    def approve_withdrawal(self, request, queryset):
        for withdrawal in queryset.filter(status='pending'):
            withdrawal.status = 'approved'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()

    def reject_withdrawal(self, request, queryset):
        for withdrawal in queryset.filter(status='pending'):
            withdrawal.status = 'rejected'
            withdrawal.processed_at = timezone.now()
            withdrawal.save()

            # Mark associated royalties as not withdrawn (if needed)
            Royalty.objects.filter(user=withdrawal.user, withdrawn=True).update(withdrawn=False)

admin.site.register(WithdrawalRequest, WithdrawalRequestAdmin)

