from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.urls import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from .models import Book, Category, BookType
from .utils import extract_first_10_pages
import json
import logging


User = get_user_model()


logger = logging.getLogger(__name__)

def home(request):
    # # Retrieve the first 12 categories in alphabetical order
    # categories = Category.objects.order_by('name')[:12]

    # context = {
    #     'categories': categories,
    # }

    return render(request, 'books/index.html')


def projects(request):
    # Get all categories
    categories = Category.objects.all()
    
    # Get all approved books
    approved_books = Book.objects.filter(is_approved=True)

    # Count books in each category
    category_book_counts = {
        category: approved_books.filter(category=category).count() for category in categories
    }

    context = {
        'categories': categories,
        'approved_books': approved_books,
        'category_book_counts': category_book_counts,
    }
    
    return render(request, 'books/project.html', context)

def projectList(request):
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
    stats = book.get_file_statistics()
    preview_url = f"/preview/{book.id}/" if book.file else None

    
    # preview_url = None
    # if book.file:
    #     book = extract_first_10_pages(book)  # Ensure preview is generated
    #     preview_url = request.build_absolute_uri(f"/preview/{book.id}/")  # Correct URL pattern

    context = {
        "book": book,
        "preview_url": preview_url,
        "page_count": stats["pages"],
        "word_count": stats["words"],
    }

    return render(request, 'books/product-details.html', context)
def department(request, category_id):
    books = Book.objects.filter(category_id=category_id, is_approved=True)
    selected_category = Category.objects.get(id=category_id)


    context = {
        'selected_category': selected_category,
    }
    return render(request, 'books/department.html', context)

@login_required(login_url='books:user_login')
def buyorsubscribe(request):
    return render(request, 'books/buyorsubscribe.html')


@login_required(login_url='books:user_login')
def payment_checkout(request):
    return render(request, 'books/paymentcheckout.html')

def subscription(request):
    return render(request, 'books/subscription.html')

@login_required(login_url='books:user_login')
def payment_method(request):
    return render(request, 'books/payment-method.html')




@login_required(login_url='books:user_login')
def login_projects(request):
    return render(request, 'books/login-project.html')

@login_required(login_url='books:user_login') 
def login_projectList(request):
    return render(request, 'books/login-list-project.html')

@login_required(login_url='books:user_login')
def login_product_details(request, id):
    return render(request, 'books/login-product-details.html', {'id': id})

@login_required(login_url='books:user_login')
def login_department(request):
    return render(request, 'books/login-department.html')

@login_required(login_url='books:user_login')
def login_buyorsubscribe(request):
    return render(request, 'books/login-buyorsubscribe.html')

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
    context = {
        'first_name': user.first_name,
        'last_name': user.last_name,
        'email': user.email,
    }
    return render(request, "books/login-index.html", context)


def verification_error(request):
    """Render the template for verification errors"""
    return render(request, 'users/verification-error.html')

@login_required(login_url='books:user_login')
def login_product_details(request, id):
    return render(request, 'books/login_product-details.html', {'id': id})


@login_required(login_url='books:user_login')
def user_settings(request):
    return render(request, 'books/settings.html')


@login_required(login_url='books:user_login')
def user_dashboard(request):
    return render(request, 'books/userdashboard.html')


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