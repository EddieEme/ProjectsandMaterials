from django.contrib import admin
from .models import Order, Payment, Download, WithdrawalRequest


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

# Register your models here.
