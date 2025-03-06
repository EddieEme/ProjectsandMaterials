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
from .models import Book, Category, BookType, Order, Download
from django.db.models import Sum, Avg, Q, Count
import json
import logging


User = get_user_model()


logger = logging.getLogger(__name__)

def home(request):
    if request.user.is_authenticated:
        return redirect('books:login-home')
    # Retrieve the first 12 categories in alphabetical order
    categories = Category.objects.order_by('name')[:12]

    context = {
        'categories': categories,
    }

    return render(request, 'books/index.html', context)


def projects(request):
    if request.user.is_authenticated:
        return redirect('books:login-project')
    # Get all categories
    categories = Category.objects.all()
    
    # Get all approved books
    books = Book.objects.filter(is_approved=True)

    # Count books in each category
    category_book_counts = {
        category: books.filter(category=category).count() for category in categories
    }
    
    print(f"this is the count {category_book_counts}")

    context = {
        'categories': categories,
        'books': books,
        'category_book_counts': category_book_counts,
    }
    
    return render(request, 'books/project.html', context)

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


def user_login(request):
    if request.user.is_authenticated:
        return redirect('books:user-dashboard')
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect('books:user-dashboard')
        else:
            messages.error(request, "Invalid login credentials.")
            return redirect('books:user_login')

    return render(request, 'books/login.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def register(request):
    if request.user.is_authenticated:
        return redirect('books:user-dashboard')
    """Register a new user."""
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")

        # Check if passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("books:register")

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("books:register")

        try:
            # Create the user (inactive until email is verified)
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_active=False
            )

            # Generate email verification token
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = default_token_generator.make_token(user)

            # Build verification link
            verification_link = request.build_absolute_uri(
                reverse('books:verify-email', kwargs={'uidb64': uid, 'token': token})
            )

            # Render the email template
            email_subject = 'Verify Your Email Address'
            email_body = render_to_string('users/email_verification.html', {
                'user': user,
                'verification_link': verification_link,
            })

            # Send the email
            email = EmailMessage(
                email_subject,
                email_body,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            email.content_subtype = 'html'  # Set email content type to HTML
            email.send()

            messages.success(request, "Registration successful! Please check your email for verification.")
            return redirect("books:user_login")  # Redirect to the login page

        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            messages.error(request, "Registration failed. Please try again.")
            return redirect("books:register")

    # Render the registration form
    return render(request, "books/register.html")

def product_details(request, id):
    book = get_object_or_404(Book, id=id)
    if request.user.is_authenticated:
        return redirect('books:login-product-details', id=book.id)
    
    stats = book.get_file_statistics()
    preview_url = f"/preview/{book.id}/" if book.file else None

    context = {
        "book": book,
        "preview_url": preview_url,
        "page_count": stats["pages"],
        "word_count": stats["words"],
    }

    return render(request, 'books/product-details.html', context)

def department(request, category_id):
    selected_category = get_object_or_404(Category, id=category_id)
    books = Book.objects.filter(category_id=category_id, is_approved=True)
    
    if request.user.is_authenticated:
        return redirect('books:login-home')

    context = {
        'selected_category': selected_category,
        'books': books,
    }
    return render(request, 'books/department.html', context)


def buyorsubscribe(request, id):
    if request.user.is_authenticated:
        return render(request, 'books/login-buyorsubscribe.html',)
    
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    context = {
        "book": book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        }
    return render(request, 'books/buyorsubscribe.html', context)


@login_required(login_url='books:user_login')
def payment_checkout(request):
    return render(request, 'books/paymentcheckout.html')

def subscription(request):
    if request.user.is_authenticated:
        return render(request, 'books/login-subscription.html')
    return render(request, 'books/subscription.html')

@login_required(login_url='books:user_login')
def payment_method(request, id):
    # Fetch the book by its ID
    book = get_object_or_404(Book, id=id)
    
    # Prepare the context
    context = {
        'book': book,
    }
    
    # Render the template with the context
    return render(request, 'books/payment-method.html', context)




@login_required(login_url='books:user_login')
def login_projects(request):
    categories = Category.objects.all()
    
    # Get all approved books
    books = Book.objects.filter(is_approved=True)

    # Count books in each category
    category_book_counts = {
        category: books.filter(category=category).count() for category in categories
    }
    
    print(f"this is the count {category_book_counts}")

    context = {
        'categories': categories,
        'books': books,
        'category_book_counts': category_book_counts,
    }
    
    return render(request, 'books/login-project.html', context)

@login_required(login_url='books:user_login') 
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


@login_required(login_url='books:user_login')
def login_department(request, category_id ):
    selected_category = get_object_or_404(Category, id=category_id)
    books = Book.objects.filter(category_id=category_id, is_approved=True)

    context = {
        'selected_category': selected_category,
        'books': books,
    }
    return render(request, 'books/login-department.html')

@login_required(login_url='books:user_login')
def login_buyorsubscribe(request, id):
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    context = {
        "book": book,
        "page_count": stats["pages"],
        "word_count": stats["words"],
        }
    return render(request, 'books/login-buyorsubscribe.html', context)

@login_required(login_url='books:user_login')
def login_subscription(request):
    return render(request, 'books/login-subscription.html')

@login_required(login_url='books:user_login')
def login_payment_method(request):
    return render(request, 'books/login-payment-method.html')

@login_required(login_url='books:user_login')
def login_home(request):
    if not request.user.is_authenticated:
        print("User is not authenticated when accessing /login-home/")
    
    user = request.user
    categories = Category.objects.order_by('name')[:12]

    context = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
        'categories': categories,
    }
    return render(request, "books/login-index.html", context)


def verification_error(request):
    """Render the template for verification errors"""
    return render(request, 'users/verification-error.html')

@login_required(login_url='books:user_login')
def login_product_details(request, id):
    book = get_object_or_404(Book, id=id)
    stats = book.get_file_statistics()
    preview_url = f"/preview/{book.id}/" if book.file else None

    context = {
        "book": book,
        "preview_url": preview_url,
        "page_count": stats["pages"],
        "word_count": stats["words"],
    }

    return render(request, 'books/login-product-details.html', context)


@login_required(login_url='books:user_login')
def user_settings(request):
    return render(request, 'books/settings.html')



@login_required(login_url='books:user_login')
def user_dashboard(request):
    user = request.user

    # Get paginated orders
    orders_qs = Order.objects.filter(user=user).order_by('-created_at')
    orders_paginator = Paginator(orders_qs, 10)
    orders_page = request.GET.get('orders_page', 1)  # Get order page number
    orders_page_obj = orders_paginator.get_page(orders_page)

    # Get paginated downloads
    downloads_qs = Download.objects.filter(user=user).order_by('-downloaded_at')
    downloads_paginator = Paginator(downloads_qs, 10)
    downloads_page = request.GET.get('downloads_page', 1)  # Get download page number
    downloads_page_obj = downloads_paginator.get_page(downloads_page)

    # Get latest download URL (if available)
    latest_download = downloads_qs.first()
    download_url = latest_download.get_download_url() if latest_download else None

    # Retrieve user's uploaded books with sales count
    products = Book.objects.filter(user=user).annotate(
        sales_count=Count('order', filter=Q(order__status='completed'))
    ).order_by('-created_at')

    total_products = products.count()
    total_sales_count = Order.objects.filter(book__user=user, status='completed').count() or 0

    # Calculate total earnings from completed orders
    total_earnings = (
        Order.objects.filter(book__user=user, status='completed')
        .aggregate(total=Sum('uploader_earning'))['total'] or 0
    )

    # Prepare context
    context = {
        'total_sales': total_sales_count,
        'total_products': total_products,
        'total_earnings': f"{total_earnings:,.2f}",
        'user': user,
        'products': products,
        'orders_page_obj': orders_page_obj,
        'downloads_page_obj': downloads_page_obj,
        'download_url': download_url,
    }

    return render(request, 'books/userdashboard.html', context)




@login_required(login_url='books:user_login')
def view_profile(request):
    user = request.user
    profile = user.profile

    context = {
        'user': user,          
        'profile': profile,     
    }
    return render(request, 'books/view-profile.html', context)

def edit_profile(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        # Update user fields
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.save()

        # Update profile fields
        profile.bio = request.POST.get('bio', profile.bio)
        profile.phone_number = request.POST.get('phone_number', profile.phone_number)
        profile.profession = request.POST.get('profession', profile.profession)

        # Handle profile picture upload
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']

        profile.save()

        messages.success(request, "Your profile has been updated successfully!")
        return redirect('books:view-profile')  # Adjust this to your actual view

    # Pass profile and user data to the template
    return render(request, 'books/edit-profile.html', {'profile': profile, 'user': user})