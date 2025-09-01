from django.contrib import admin
from .models import Book, BookType, Category, HireWriterRequest
from django.utils import timezone


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'book_type', 'category', 'price', 'is_approved', 'created_at', 'user', 'updated_at', 'preview_url')
    list_filter = ('is_approved', 'author', 'category', 'created_at')
    search_fields = ('title', 'author', 'category', 'book_type')
    actions = ['approve_books']

    def approve_books(self, request, queryset):
        queryset.update(is_approved=True)
    approve_books.short_description = "Approve selected books"
    


@admin.register(HireWriterRequest)
class HireWriterRequestAdmin(admin.ModelAdmin):
    list_display = ('topic', 'service', 'name','email','phone', 'status','created_at', )
    list_filter = ( 'created_at','status',)
    search_fields = ('services__name', 'name', 'email', 'topic', 'phone')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    
    actions = ['mark_as_reviewing', 'mark_as_in_progress', 'mark_as_completed', 'mark_as_cancelled']

    def mark_as_reviewing(self, request, queryset):
        queryset.update(status='reviewing')
    mark_as_reviewing.short_description = "Mark selected requests as Reviewing"

    def mark_as_in_progress(self, request, queryset):
        queryset.update(status='in_progress')
    mark_as_in_progress.short_description = "Mark selected requests as In Progress"

    def mark_as_completed(self, request, queryset):
        queryset.update(status='completed')
    mark_as_completed.short_description = "Mark selected requests as Completed"

    def mark_as_cancelled(self, request, queryset):
        queryset.update(status='cancelled')
    mark_as_cancelled.short_description = "Mark selected requests as Cancelled"
    
    
admin.site.register(BookType)
admin.site.register(Category)





