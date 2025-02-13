from django.shortcuts import redirect, render
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
import logging


User = get_user_model()


logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'books/index.html')


def projects(request):
    return render(request, 'books/project.html')

def projectList(request):
    return render(request, 'books/list-project.html')


def user_login(request):
    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(email=email, password=password)

        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('books:login-home')
            else:
                messages.error(request, "Your account has not been activated yet.")
                return render(request, 'books/login.html')
        else:
            messages.error(request, "Invalid login credentials.")
            return render(request, 'books/login.html')

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
    return render(request, 'books/product-details.html', {'id': id})

def department(request):
    return render(request, 'books/department.html')


def buyorsubscribe(request):
    return render(request, 'books/buyorsubscribe.html')

def subscription(request):
    return render(request, 'books/subscription.html')

def payment_method(request):
    return render(request, 'books/payment-method.html')




@login_required(login_url='books:login')
def login_projects(request):
    return render(request, 'books/login-project.html')

@login_required(login_url='books:login') 
def login_projectList(request):
    return render(request, 'books/login-list-project.html')

@login_required(login_url='books:login')
def login_product_details(request, id):
    return render(request, 'books/login-product-details.html', {'id': id})

@login_required(login_url='books:login')
def login_department(request):
    return render(request, 'books/login-department.html')

@login_required(login_url='books:login')
def login_buyorsubscribe(request):
    return render(request, 'books/login-buyorsubscribe.html')

@login_required(login_url='books:login')
def login_subscription(request):
    return render(request, 'books/login-subscription.html')

@login_required(login_url='books:login')
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



def verification_already_done(request):
    """Render the template for already verified users"""
    return render(request, 'users/verification-already-done.html')

def verification_error(request):
    """Render the template for verification errors"""
    return render(request, 'users/verification-error.html')

def verification_success(request):
    """Render the template for successful verification"""
    return render(request, 'users/verification-success.html')


