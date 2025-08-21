from django.contrib import admin
from .models import Book, BookType, Category
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
    
    
admin.site.register(BookType)
admin.site.register(Category)




