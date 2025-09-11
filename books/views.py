import datetime
import os
from re import template
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.contrib import messages
from django.urls import reverse
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from datetime import datetime, timedelta


from books.utils import generate_preview_task
from .models import Book, Category, BookType, HireWriterRequest
from payments.models import  Order, Download, Payment
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

@login_required(login_url='users:user_login')
def hire(request):
    if request.method == 'POST':
        service = request.POST.get('service')
        name = request.POST.get('name')
        email = request.POST.get('email')
        topic = request.POST.get('topic')
        phone = request.POST.get('phone')
        description = request.POST.get('description')
        format_file = request.FILES.get('format')

        # Validate required fields
        if not all([service, name, email, topic, phone, description]):
            return JsonResponse({'error': 'All required fields must be filled.'}, status=400)

        # Validate email
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'error': 'Please enter a valid email address.'}, status=400)

        # Save to DB
        writer_request = HireWriterRequest.objects.create(
            user=request.user if request.user.is_authenticated else None,
            service=service,
            name=name,
            email=email,
            topic=topic,
            phone=phone,
            description=description,
            upload_format=format_file
        )

        # Send email
        try:
            subject = f"New Writer Request from {name}"
            message = f"""
New request received:

Name: {name}
Email: {email}
Phone: {phone}
Service: {service}
Topic: {topic}
Description: {description}
File Uploaded: {'Yes' if format_file else 'No'}
"""
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.SERVER_EMAIL],
                fail_silently=False,
            )
        except Exception as e:
            return JsonResponse({'error': f'Failed to send request: {str(e)}'}, status=500)

        return JsonResponse({
            'message': 'Request submitted successfully!',
            'redirect': '#successMessage'
        })

    return render(request, 'books/hire.html')




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
    # Get the selected book type, category, and search query
    book_type_slug = request.GET.get('book_type', '')
    category_slug = request.GET.get('category', '')
    search_query = request.GET.get('q', '')

    # Get all books initially
    books = Book.objects.filter(is_approved=True)

    # Filter by book type if selected
    if book_type_slug:
        books = books.filter(book_type__slug=book_type_slug)

    # Filter by category if selected
    if category_slug:
        books = books.filter(category__slug=category_slug)

    # Filter by search query if provided
    if search_query:
        books = books.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(author__icontains=search_query)
        )

    # Pagination
    paginator = Paginator(books, 12)  # 10 books per page
    page_number = request.GET.get('page')
    books_page = paginator.get_page(page_number)

    # Get all distinct book types and categories for the dropdown options
    book_types = BookType.objects.all()
    categories = Category.objects.all()

    context = {
        'books': books_page,
        'selected_book_type': book_type_slug,
        'selected_category': category_slug,
        'search_query': search_query,
        'book_types': book_types,
        'categories': categories,
    }

    template = 'books/login-list-project.html' if request.user.is_authenticated else 'books/list-project.html'
    return render(request, template, context)




@cache_page(60 * 15)
def product_details(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),
        slug=slug
    )

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
            .order_by('-created_at')[:5]
        )
        cache.set(related_cache_key, related_books, 60 * 60 * 12)

    # Get preview attempts with 24-hour time-based reset
    preview_data = get_preview_data(request)
    preview_attempts_remaining = max(0, 3 - preview_data['count'])
    reset_date = preview_data['reset_date']
    
    context = {
        "book": book,
        "related_books": related_books,
        "preview_attempts_remaining": preview_attempts_remaining,
        "reset_date": reset_date,
    }
    
    template = 'books/login-product-details.html' if request.user.is_authenticated else 'books/product-details.html'
    return render(request, template, context)





# @cache_page(60 * 15)
# @login_required(login_url='users:user_login')
# def login_product_details(request, slug):
   
#     book = get_object_or_404(
#         Book.objects.select_related('book_type', 'category', 'user')
#                    .defer('description', 'file'),  
#         slug=slug
#     )

#     related_cache_key = f"related_books_{book.slug}"
#     related_books = cache.get(related_cache_key)
#     if not related_books:
#         title_keywords = [word for word in book.title.split() if len(word) > 3][:3]
#         query = Q()
#         for word in title_keywords:
#             query |= Q(title__icontains=word) | Q(description__icontains=word)
        
#         related_books = (
#             Book.objects
#             .filter(query)
#             .exclude(slug=book.slug)
#             .only('slug', 'title', 'cover_image', 'price')
#             .order_by('-created_at')[:5]
#         )
#         cache.set(related_cache_key, related_books, 60 * 60 * 12)

#     context = {
#         "book": book,
#         "related_books": related_books,
#     }

#     return render(request, 'books/login-product-details.html', context)



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
    
    return render(request, "books/upload_book.html", {"faculties": faculties, "departments": departments, 'next': request.GET.get('next', 'books:upload-book')})
    
    
    
# def preview_pdf(request, slug):
#     # Only include actual relational fields in select_related
#     book = get_object_or_404(
#         Book.objects.select_related('book_type', 'category', 'user')
#                    .defer('description', 'file'),  
#         slug=slug
#     )
    
#     stats = book.get_file_statistics()
    
#     template = 'books/login-preview.html' if request.user.is_authenticated else 'books/preview.html'
   
#     context = {
#         'book': book,
#         "page_count": stats["pages"],
#         "word_count": stats["words"],
#         'stats': stats,
#     }
   
#     return render(request, template, context)


def preview_pdf(request, slug):
    book = get_object_or_404(
        Book.objects.select_related('book_type', 'category', 'user')
                   .defer('description', 'file'),  
        slug=slug
    )
    
    # Get or update preview attempts with 24-hour time-based reset
    preview_data = get_preview_data(request)
    
    # Check if user has exceeded global preview limit
    if preview_data['count'] >= 3:
        messages.warning(request, 'You have reached the maximum preview limit. Your previews will reset on {}.'.format(
            preview_data['reset_date'].strftime('%Y-%m-%d at %H:%M')
        ))
        return redirect('books:product-details', slug=slug)
    
    # Increment global preview count
    preview_data['count'] += 1
    set_preview_data(request, preview_data)
    
    stats = book.get_file_statistics()
    
    template = 'books/login-preview.html' if request.user.is_authenticated else 'books/preview.html'
   
    context = {
        'book': book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        'stats': stats,
        'preview_attempts_remaining': 3 - preview_data['count'],
        'reset_date': preview_data['reset_date'],
    }
   
    return render(request, template, context)


# Helper functions for 24-hour time-based preview tracking
def get_preview_data(request):
    """Get preview data with 24-hour time-based reset logic"""
    now = datetime.now()
    
    if 'preview_data' not in request.session:
        # Initialize new preview data with 24-hour reset
        reset_date = now + timedelta(hours=24)
        preview_data = {
            'count': 0,
            'reset_date': reset_date.isoformat(),
            'created_date': now.isoformat()
        }
        request.session['preview_data'] = json.dumps(preview_data)
        return preview_data
    
    # Load existing preview data
    preview_data = json.loads(request.session['preview_data'])
    reset_date = datetime.fromisoformat(preview_data['reset_date'])
    created_date = datetime.fromisoformat(preview_data['created_date'])
    
    # Check if 24-hour reset period has passed
    if now >= reset_date:
        # Reset the counter and set new 24-hour reset date
        new_reset_date = now + timedelta(hours=24)
        preview_data = {
            'count': 0,
            'reset_date': new_reset_date.isoformat(),
            'created_date': now.isoformat()
        }
        request.session['preview_data'] = json.dumps(preview_data)
    
    # Convert string dates back to datetime objects for return
    preview_data['reset_date'] = datetime.fromisoformat(preview_data['reset_date'])
    preview_data['created_date'] = datetime.fromisoformat(preview_data['created_date'])
    
    return preview_data


def set_preview_data(request, preview_data):
    """Store preview data in session"""
    # Convert datetime objects to strings for JSON serialization
    data_to_store = preview_data.copy()
    data_to_store['reset_date'] = data_to_store['reset_date'].isoformat()
    data_to_store['created_date'] = data_to_store['created_date'].isoformat()
    
    request.session['preview_data'] = json.dumps(data_to_store)
    request.session.modified = True
