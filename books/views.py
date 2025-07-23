from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from .models import Book, Category, BookType
from payments.models import  Order, Download
from django.db.models import Sum, Avg, Q, Count
from django.views.decorators.cache import cache_page
from django.core.cache import cache
import json
import logging
import bleach


User = get_user_model()


logger = logging.getLogger(__name__)


from django.shortcuts import render
from .models import BookType, Category

def home(request):
    # Retrieve the first 12 BookTypes and 20 Categories in alphabetical order
    faculties = BookType.objects.order_by('name')[:40]
    categories = Category.objects.order_by('name')[:60]
    
    context = {
        'faculties': faculties,
        'categories': categories,
        'user': request.user if request.user.is_authenticated else None,  # Fixed syntax error
    }

    template = 'books/login-index.html' if request.user.is_authenticated else 'books/index.html'
    return render(request, template, context)


def services(request):
    template = 'books/login-services.html' if request.user.is_authenticated else 'books/services.html'
    context = {}
    return render(request, template, context)
    

def resources(request):
    template = 'books/login-resources.html' if request.user.is_authenticated else 'books/resources.html'
    context = {}
    return render(request, template, context)


def faculty(request, book_type_id):
    # Get all book types (faculties)
    faculties = BookType.objects.order_by('name')

    # Get all categories
    categories = Category.objects.order_by('name')

    # Get the selected book type (faculty)
    selected_book_type = get_object_or_404(BookType, id=book_type_id)

    books_list = Book.objects.filter(book_type=selected_book_type, is_approved=True)

    # Paginate the books (10 per page)
    paginator = Paginator(books_list, 10)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)

    # Count books per book_type (faculty) for display
    faculty_book_counts = {
        book_type.id: Book.objects.filter(book_type=book_type, is_approved=True).count()
        for book_type in faculties
    }

    context = {
        'selected_book_type': selected_book_type,
        'books': books,
        'faculties': faculties,
        'categories': categories,
        'faculty_book_counts': faculty_book_counts,
    }

    template = 'books/login_faculty.html' if request.user.is_authenticated else 'books/faculty.html'
    return render(request, template, context)




def category_books(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    books_list = Book.objects.filter(category=category, is_approved=True)  # Ensure only approved books
    categories = Category.objects.all()

    # Pagination (10 books per page)
    paginator = Paginator(books_list, 10)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)  # Paginated books

    # Count books in each category using books_list (QuerySet)
    category_book_counts = {
        cat.id: Book.objects.filter(category=cat, is_approved=True).count() for cat in categories
    }

    context = {
        "category": category,
        "books": books,  # Paginated books
        "categories": categories,
        "category_book_counts": category_book_counts,  # Book count per category
    }
    template = 'books/login-department.html' if request.user.is_authenticated else 'books/department.html'
    return render(request, template, context)




from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def projects(request):
    if request.user.is_authenticated:
        return redirect('books:login-project')

    # Get all categories
    categories = Category.objects.all()
    
    # Get all approved books
    books_list = Book.objects.filter(is_approved=True)

    # Pagination: Show 5 books per page
    paginator = Paginator(books_list, 20)  # Show 5 books per page
    page_number = request.GET.get('page')

    try:
        books = paginator.get_page(page_number)
    except PageNotAnInteger:
        books = paginator.get_page(1)  # If page is not an integer, deliver first page
    except EmptyPage:
        books = paginator.get_page(paginator.num_pages)  # If page is out of range, deliver last page

    # Count books in each category
    category_book_counts = {
        category: books_list.filter(category=category).count() for category in categories
    }

    context = {
        'categories': categories,
        'books': books,  # Paginated books
        'category_book_counts': category_book_counts,
    }
    template = 'books/login-project.html' if request.user.is_authenticated else 'books/project.html'
    return render(request,template , context)

def projects_by_faculty(request):
   
    # Get all categories
    categories = Category.objects.all()
    faculties = BookType.objects.order_by('name')    
    
    # Get all approved books
    books_list = Book.objects.filter(is_approved=True)

    # Pagination: Show 5 books per page
    paginator = Paginator(books_list, 20)  # Show 5 books per page
    page_number = request.GET.get('page')

    try:
        books = paginator.get_page(page_number)
    except PageNotAnInteger:
        books = paginator.get_page(1)  # If page is not an integer, deliver first page
    except EmptyPage:
        books = paginator.get_page(paginator.num_pages)  # If page is out of range, deliver last page

    # Count books in each category
    faculty_book_counts = {
        book_type.id: Book.objects.filter(book_type=book_type, is_approved=True).count()
        for book_type in faculties
    }

    context = {
        'faculties': faculties,
        'books': books,  # Paginated books
        'faculty_book_counts': faculty_book_counts,
    }
    template = 'books/login-project_faculty.html' if request.user.is_authenticated else 'books/project_faculty.html'
    return render(request,template , context)

def projectList(request):
    if request.user.is_authenticated:
        return redirect('books:login-project-list')
     # Get the selected book type and category from the request
    book_type_id = request.GET.get('book_type', '')
    category_id = request.GET.get('category', '')

    # Get all books initially
    books = Book.objects.filter(is_approved=True)

    # Filter by book type if selected
    if book_type_id:
        books = books.filter(book_type__id=book_type_id)

    # Filter by category if selected
    if category_id:
        books = books.filter(category__id=category_id)

    # Get all distinct book types and categories for the dropdown options
    book_types = BookType.objects.all()
    categories = Category.objects.all()

    # Pass selected values to the template for retaining user selections
    context = {
        'books': books,
        'selected_book_type': book_type_id,
        'selected_category': category_id,
        'book_types': book_types,
        'categories': categories,
    }

    return render(request, 'books/list-project.html', context)




@cache_page(60 * 15)
def product_details(request, id):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  # Defer large fields
        id=id
    )

    if request.user.is_authenticated:
        return redirect('books:login-product-details', id=book.id)

    # Related books logic (cached)
    related_cache_key = f"related_books_{book.id}"
    related_books = cache.get(related_cache_key)
    if not related_books:
        title_keywords = [word for word in book.title.split() if len(word) > 3][:3]
        query = Q()
        for word in title_keywords:
            query |= Q(title__icontains=word) | Q(description__icontains=word)
        
        related_books = (
            Book.objects
            .filter(query)
            .exclude(id=book.id)
            .only('id', 'title', 'cover_image', 'price')
            .order_by('-created_at')[:5]  # More predictable than random
        )
        cache.set(related_cache_key, related_books, 60 * 60 * 12)  # Cache for 12 hours

    context = {
        "book": book,
        "related_books": related_books,
    }

    return render(request, 'books/product-details.html', context)



@login_required(login_url='users:user_login')
def payment_checkout(request):
    return render(request, 'books/paymentcheckout.html')



@login_required(login_url='users:user_login')
def payment_method(request, id):
    # Fetch the book by its ID
    book = get_object_or_404(Book, id=id)
    
    # Prepare the context
    context = {
        'book': book,
    }
    
    # Render the template with the context
    return render(request, 'books/payment-method.html', context)




@login_required(login_url='users:user_login')
def login_projects(request):
  # Get all categories
    categories = Category.objects.all()
    
    # Get all approved books
    books_list = Book.objects.filter(is_approved=True)

    # Pagination: Show 5 books per page
    paginator = Paginator(books_list, 20)  # Show 5 books per page
    page_number = request.GET.get('page')

    try:
        books = paginator.get_page(page_number)
    except PageNotAnInteger:
        books = paginator.get_page(1)  # If page is not an integer, deliver first page
    except EmptyPage:
        books = paginator.get_page(paginator.num_pages)  # If page is out of range, deliver last page

    # Count books in each category
    category_book_counts = {
        category: books_list.filter(category=category).count() for category in categories
    }

    context = {
        'categories': categories,
        'books': books,  # Paginated books
        'category_book_counts': category_book_counts,
    }
    
    return render(request, 'books/login-project.html', context)

@login_required(login_url='users:user_login') 
def login_projectList(request):
    book_type_id = request.GET.get('book_type', '')
    category_id = request.GET.get('category', '')

    # Get all books initially
    books = Book.objects.filter(is_approved=True)

    # Filter by book type if selected
    if book_type_id:
        books = books.filter(book_type__id=book_type_id)

    # Filter by category if selected
    if category_id:
        books = books.filter(category__id=category_id)

    # Get all distinct book types and categories for the dropdown options
    book_types = BookType.objects.all()
    categories = Category.objects.all()

    # Pass selected values to the template for retaining user selections
    context = {
        'books': books,
        'selected_book_type': book_type_id,
        'selected_category': category_id,
        'book_types': book_types,
        'categories': categories,
    }
    return render(request, 'books/login-list-project.html', context)








@login_required(login_url='users:user_login')
def login_payment_method(request):
    return render(request, 'books/login-payment-method.html')




def verification_error(request):
    """Render the template for verification errors"""
    return render(request, 'users/verification-error.html')


@cache_page(60 * 15)
@login_required(login_url='users:user_login')
def login_product_details(request, id):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  # Defer large fields
        id=id
    )

    related_cache_key = f"related_books_{book.id}"
    related_books = cache.get(related_cache_key)
    if not related_books:
        title_keywords = [word for word in book.title.split() if len(word) > 3][:3]
        query = Q()
        for word in title_keywords:
            query |= Q(title__icontains=word) | Q(description__icontains=word)
        
        related_books = (
            Book.objects
            .filter(query)
            .exclude(id=book.id)
            .only('id', 'title', 'cover_image', 'price')
            .order_by('-created_at')[:5]  # More predictable than random
        )
        cache.set(related_cache_key, related_books, 60 * 60 * 12)  # Cache for 12 hours

    context = {
        "book": book,
        "related_books": related_books,
    }

    return render(request, 'books/login-product-details.html', context)


from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Book, BookType, Category
from django.core.files.storage import default_storage

def upload_book(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        author = request.POST.get("author")
        book_type_id = request.POST.get("book_type")
        category_id = request.POST.get("category")
        file = request.FILES.get("file")
        cover_image = request.FILES.get("cover_image")

        # Sanitize the description field
        cleaned_description = bleach.clean(
            description,
            tags=['p', 'strong', 'em', 'ul', 'li', 'a', 'br'],  # Allowed tags
            attributes={'a': ['href', 'title']}  # Allowed attributes for <a>
        )

        # Check if a book with the same title exists (case-insensitive)
        if Book.objects.filter(title__iexact=title).exists():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "message": "A book with this title already exists."}, status=400)
            else:
                messages.error(request, "A book with this title already exists.")
                return redirect("books:upload-book")

        # Validate file type
        if file:
            allowed_extensions = ["pdf", "docx"]
            file_extension = file.name.split(".")[-1].lower()
            if file_extension not in allowed_extensions:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "message": "Only PDF and DOCX files are allowed."}, status=400)
                else:
                    messages.error(request, "Only PDF and DOCX files are allowed.")
                    return redirect("books:upload-book")
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "message": "Book file is required."}, status=400)
            else:
                messages.error(request, "Book file is required.")
                return redirect("books:upload-book")

        # Handle book type (faculty)
        try:
            # Check if creating a new faculty
            if request.POST.get("book_type_name"):
                book_type_name = request.POST.get("book_type_name")
                # Check if a faculty with this name already exists
                existing_type = BookType.objects.filter(name__iexact=book_type_name).first()
                if existing_type:
                    book_type = existing_type
                else:
                    book_type = BookType.objects.create(name=book_type_name)
            else:
                book_type = BookType.objects.get(id=book_type_id)
        except BookType.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "message": "Selected faculty does not exist."}, status=400)
            else:
                messages.error(request, "Selected faculty does not exist.")
                return redirect("books:upload-book")

        # Handle category (department)
        try:
            # Check if creating a new department
            if request.POST.get("category_name"):
                category_name = request.POST.get("category_name")
                # Check if a department with this name already exists
                existing_category = Category.objects.filter(name__iexact=category_name).first()
                if existing_category:
                    category = existing_category
                else:
                    category = Category.objects.create(name=category_name, book_type=book_type)
            else:
                category = Category.objects.get(id=category_id)
        except Category.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "message": "Selected department does not exist."}, status=400)
            else:
                messages.error(request, "Selected department does not exist.")
                return redirect("books:upload-book")

        try:
            # Save the book with a fixed price of ₦5,000
            book = Book.objects.create(
                title=title,
                description=cleaned_description,  # Use the sanitized description
                author=author,
                book_type=book_type,
                category=category,
                price=5000,
                file=file,
                cover_image=cover_image,
                user=request.user
            )

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": True, "message": "Book uploaded successfully!"})
            else:
                messages.success(request, "Book uploaded successfully!")
                
                return redirect("books:upload-book")

        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "message": f"Error creating book: {str(e)}"}, status=500)
            else:
                messages.error(request, f"Error creating book: {str(e)}")
                return redirect("books:upload-book")

    # Fetch all faculties and departments for the form
    faculties = BookType.objects.all()
    departments = Category.objects.all()
    return render(request, "books/upload_book.html", {"faculties": faculties, "departments": departments})