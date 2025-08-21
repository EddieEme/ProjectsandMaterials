from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
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


from books.utils import generate_preview_task
from .models import Book, Category, BookType
from payments.models import  Order, Download
from django.db.models import Sum, Avg, Q, Count
from django.views.decorators.cache import cache_page
from django.core.files.storage import default_storage
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


def faculty(request, slug):
    faculties = BookType.objects.order_by('name')
    categories = Category.objects.order_by('name')
    selected_book_type = get_object_or_404(BookType, slug=slug)

    books_list = Book.objects.filter(book_type=selected_book_type, is_approved=True)
    
    # Pagination
    paginator = Paginator(books_list, 10)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)

    # Count books per faculty
    faculty_book_counts = {
        book_type.slug: Book.objects.filter(book_type=book_type, is_approved=True).count()
        for book_type in faculties
    }

    # Count books per category for each faculty
    faculty_category_counts = {}
    for faculty in faculties:
        faculty_category_counts[faculty.slug] = {
            category.slug: Book.objects.filter(
                book_type=faculty,
                category=category,  # ForeignKey lookup (not many-to-many)
                is_approved=True
            ).count()
            for category in categories
        }

    context = {
        'selected_book_type': selected_book_type,
        'books': books,
        'faculties': faculties,
        'categories': categories,
        'faculty_book_counts': faculty_book_counts,
        'faculty_category_counts': faculty_category_counts,
    }

    print(f"here is the name of the faculty {selected_book_type.name}")

    template = 'books/login_faculty.html' if request.user.is_authenticated else 'books/faculty.html'
    return render(request, template, context)





def category_books(request, slug):
    category = get_object_or_404(Category, slug=slug)
    books_list = Book.objects.filter(category=category, is_approved=True)  # Ensure only approved books
    categories = Category.objects.all()

    # Pagination (10 books per page)
    paginator = Paginator(books_list, 10)
    page_number = request.GET.get("page")
    books = paginator.get_page(page_number)  # Paginated books

    # Count books in each category using books_list (QuerySet)
    category_book_counts = {
        cat.slug: Book.objects.filter(category=cat, is_approved=True).count() for cat in categories
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
        book_type.slug: Book.objects.filter(book_type=book_type, is_approved=True).count()
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
    book_type_slug = request.GET.get('book_type', '')
    category_slug = request.GET.get('category', '')

    # Get all books initially
    books = Book.objects.filter(is_approved=True)

    # Filter by book type if selected
    if book_type_slug:
        books = books.filter(book_type__slug=book_type_slug)

    # Filter by category if selected
    if category_slug:
        books = books.filter(category__slug=category_slug)

    # Get all distinct book types and categories for the dropdown options
    book_types = BookType.objects.all()
    categories = Category.objects.all()

    # Pass selected values to the template for retaining user selections
    context = {
        'books': books,
        'selected_book_type': book_type_slug,
        'selected_category': category_slug,
        'book_types': book_types,
        'categories': categories,
    }

    return render(request, 'books/list-project.html', context)




@cache_page(60 * 15)
def product_details(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  # Defer large fields
        slug=slug
    )

    if request.user.is_authenticated:
        return redirect('books:login-product-details', slug=book.slug)

    # Related books logic (cached)
    related_cache_key = f"related_books_{book.slug}"
    related_books = cache.get(related_cache_key)
    if not related_books:
        title_keywords = [word for word in book.title.split() if len(word) > 3][:3]
        query = Q()
        for word in title_keywords:
            query |= Q(title__icontains=word) | Q(description__icontains=word)
        
        related_books = (
            Book.objects
            .filter(query)
            .exclude(slug=book.slug)
            .only('slug', 'title', 'cover_image', 'price')
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
def payment_method(request, slug):
    # Fetch the book by its slug
    book = get_object_or_404(Book, slug=slug)
    
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
    book_type_slug = request.GET.get('book_type', '')
    category_slug = request.GET.get('category', '')

    # Get all books initially
    books = Book.objects.filter(is_approved=True)

    # Filter by book type if selected
    if book_type_slug:
        books = books.filter(book_type__slug=book_type_slug)

    # Filter by category if selected
    if category_slug:
        books = books.filter(category__slug=category_slug)

    # Get all distinct book types and categories for the dropdown options
    book_types = BookType.objects.all()
    categories = Category.objects.all()

    # Pass selected values to the template for retaining user selections
    context = {
        'books': books,
        'selected_book_type': book_type_slug,
        'selected_category': category_slug,
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
def login_product_details(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  
        slug=slug
    )

    related_cache_key = f"related_books_{book.slug}"
    related_books = cache.get(related_cache_key)
    if not related_books:
        title_keywords = [word for word in book.title.split() if len(word) > 3][:3]
        query = Q()
        for word in title_keywords:
            query |= Q(title__icontains=word) | Q(description__icontains=word)
        
        related_books = (
            Book.objects
            .filter(query)
            .exclude(slug=book.slug)
            .only('slug', 'title', 'cover_image', 'price')
            .order_by('-created_at')[:5]  # More predictable than random
        )
        cache.set(related_cache_key, related_books, 60 * 60 * 12)  # Cache for 12 hours

    context = {
        "book": book,
        "related_books": related_books,
    }

    return render(request, 'books/login-product-details.html', context)


@login_required(login_url='users:user_login')
def upload_book(request):
    # Check if it's an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        author = request.POST.get("author")
        book_type_value = request.POST.get("book_type") 
        category_value = request.POST.get("category")    
        file = request.FILES.get("file")
        cover_image = request.FILES.get("cover_image")

        # Validate required fields
        missing_fields = []
        if not title: missing_fields.append("title")
        if not description: missing_fields.append("description")
        if not author: missing_fields.append("author")
        if not file: missing_fields.append("file")
        if not book_type_value and not request.POST.get("book_type_name"): 
            missing_fields.append("faculty")
        if not category_value and not request.POST.get("category_name"): 
            missing_fields.append("department")
        
        if missing_fields:
            error_msg = f"Missing required fields: {', '.join(missing_fields)}"
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("books:upload-book")

        # Check for duplicate title
        if Book.objects.filter(title__iexact=title).exists():
            error_msg = "A book with this title already exists."
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("books:upload-book")

        # Validate file type
        if file:
            allowed_extensions = ["pdf", "docx", "doc"]
            file_extension = file.name.split(".")[-1].lower()
            if file_extension not in allowed_extensions:
                error_msg = "Only PDF and DOCX files are allowed."
                if is_ajax:
                    return JsonResponse({"success": False, "message": error_msg}, status=400)
                else:
                    messages.error(request, error_msg)
                    return redirect("books:upload-book")

        # Handle book type (faculty)
        try:
            if request.POST.get("book_type_name"):
                book_type_name = request.POST.get("book_type_name").strip()
                if not book_type_name:
                    raise ValueError("Faculty name cannot be empty")
                
                existing_type = BookType.objects.filter(name__iexact=book_type_name).first()
                if existing_type:
                    book_type = existing_type
                else:
                    book_type = BookType.objects.create(name=book_type_name)
            else:
                if not book_type_value:
                    raise ValueError("Faculty selection is required")
                
                try:
                    book_type = BookType.objects.get(slug=book_type_value)
                except BookType.DoesNotExist:
                    try:
                        book_type = BookType.objects.get(id=int(book_type_value))
                    except (ValueError, BookType.DoesNotExist):
                        raise BookType.DoesNotExist("Selected faculty does not exist.")
                        
        except (BookType.DoesNotExist, ValueError) as e:
            error_msg = str(e) if isinstance(e, ValueError) else "Selected faculty does not exist."
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("books:upload-book")

        # Handle category (department)
        try:
            if request.POST.get("category_name"):
                category_name = request.POST.get("category_name").strip()
                if not category_name:
                    raise ValueError("Department name cannot be empty")
                
                existing_category = Category.objects.filter(
                    name__iexact=category_name, 
                    book_type=book_type
                ).first()
                
                if existing_category:
                    category = existing_category
                else:
                    category = Category.objects.create(name=category_name, book_type=book_type)
            else:
                if not category_value:
                    raise ValueError("Department selection is required")
                
                try:
                    category = Category.objects.get(slug=category_value, book_type=book_type)
                except Category.DoesNotExist:
                    try:
                        category = Category.objects.get(id=int(category_value), book_type=book_type)
                    except (ValueError, Category.DoesNotExist):
                        raise Category.DoesNotExist("Selected department does not exist.")
                        
        except (Category.DoesNotExist, ValueError) as e:
            error_msg = str(e) if isinstance(e, ValueError) else "Selected department does not exist."
            if is_ajax:
                return JsonResponse({"success": False, "message": error_msg}, status=400)
            else:
                messages.error(request, error_msg)
                return redirect("books:upload-book")

        # Create the book
        try:
            # Sanitize the description field
            cleaned_description = bleach.clean(
                description,
                tags=['p', 'strong', 'em', 'ul', 'li', 'a', 'br'],
                attributes={'a': ['href', 'title']},
                strip=True
            )

            book = Book.objects.create(
                title=title,
                description=cleaned_description,
                author=author,
                book_type=book_type,
                category=category,
                price=5000,
                file=file,
                cover_image=cover_image,
                user=request.user,
                preview_url=None 
            )

            # Generate preview asynchronously - IMPORTANT: Use .delay() for async
            try:
                generate_preview_task.delay(book.id)
                print(f"Preview generation task queued for book {book.id}")
            except Exception as e:
                print(f"Failed to queue preview generation: {e}")
                
            if is_ajax:
                return JsonResponse({
                    "success": True, 
                    "message": "Book uploaded successfully! Preview will be generated shortly.",
                    "book_id": book.id
                })
            else:
                messages.success(request, "Book uploaded successfully! Preview will be generated shortly.")
                return redirect("books:upload-book")

        except Exception as e:
            print(f"Error creating book: {str(e)}")
            if is_ajax:
                return JsonResponse({"success": False, "message": "Error creating book. Please try again."}, status=500)
            else:
                messages.error(request, "Error creating book. Please try again.")
                return redirect("books:upload-book")

    # GET request handling
    if is_ajax:
        return JsonResponse({"success": False, "message": "GET method not allowed"}, status=405)
    
    faculties = BookType.objects.all()
    departments = Category.objects.all()
    
    return render(request, "books/upload_book.html", {
        "faculties": faculties, 
        "departments": departments
    })
    
    
    
def preview_pdf(request, slug):
    # Only include actual relational fields in select_related
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  
        slug=slug
    )
    
    file_stats = book.get_file_statistics()
    
    template = 'books/login-preview.html' if request.user.is_authenticated else 'books/preview.html'
   
    context = {
        'book': book,
        'file_stats': file_stats,
    }
   
    return render(request, template, context)
