import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectsandmaterial.settings')
django.setup()

from django.utils.text import slugify
from django.utils.crypto import get_random_string
from books.models import Book, BookType, Category

def fix_slugs():
    print('Fixing duplicate slugs...')
    
    # Fix BookType slugs
    print('Fixing BookType slugs...')
    book_types = BookType.objects.all()
    for book_type in book_types:
        if not book_type.slug:
            base_slug = slugify(book_type.name) or "booktype"
            book_type.slug = base_slug
        
        # Check for duplicates and make unique
        counter = 1
        original_slug = book_type.slug
        while BookType.objects.filter(slug=book_type.slug).exclude(id=book_type.id).exists():
            book_type.slug = f"{original_slug}-{counter}"
            counter += 1
            if counter > 100:
                book_type.slug = f"{original_slug}-{get_random_string(4).lower()}"
                break
        
        book_type.save()
        print(f'  Fixed: {book_type.name} -> {book_type.slug}')
    
    # Fix Category slugs
    print('Fixing Category slugs...')
    categories = Category.objects.all()
    for category in categories:
        if not category.slug:
            base_slug = slugify(category.name) or "category"
            category.slug = base_slug
        
        # Check for duplicates and make unique
        counter = 1
        original_slug = category.slug
        while Category.objects.filter(slug=category.slug).exclude(id=category.id).exists():
            category.slug = f"{original_slug}-{counter}"
            counter += 1
            if counter > 100:
                category.slug = f"{original_slug}-{get_random_string(4).lower()}"
                break
        
        category.save()
        print(f'  Fixed: {category.name} -> {category.slug}')
    
    # Fix Book slugs
    print('Fixing Book slugs...')
    books = Book.objects.all()
    for book in books:
        if not book.slug:
            base_slug = slugify(book.title) or "book"
            book.slug = base_slug
        
        # Check for duplicates and make unique
        counter = 1
        original_slug = book.slug
        while Book.objects.filter(slug=book.slug).exclude(id=book.id).exists():
            book.slug = f"{original_slug}-{counter}"
            counter += 1
            if counter > 100:
                book.slug = f"{original_slug}-{get_random_string(6).lower()}"
                break
        
        book.save()
        print(f'  Fixed: {book.title} -> {book.slug}')
    
    print('Successfully fixed all slugs!')

if __name__ == '__main__':
    fix_slugs()