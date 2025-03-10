from django.shortcuts import redirect, render
from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.urls import reverse
from django.conf import settings
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from payments.models import Order, Download
from books.models import Book
from books.utils import download_book
from django.core.paginator import Paginator
from django.db.models import Count, Sum, Q



from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token


from .serializers import *

import logging

logger = logging.getLogger(__name__)

User = get_user_model() 

def user_login(request):
    if request.user.is_authenticated:
        # Check if the user is a superuser
        if request.user.is_superuser:
            return redirect('admin_app:batch-upload-books')  # Redirect to admin_app dashboard
        return redirect('users:user-dashboard')  # Redirect normal users

    if request.method == "POST":
        email = request.POST['email']
        password = request.POST['password']

        user = authenticate(email=email, password=password)

        if user is not None:
            login(request, user)

            # Redirect based on user type
            if user.is_superuser:
                return redirect('admin_app:batch-upload-books')  # Redirect to admin_app
            return redirect('users:user-dashboard')  # Redirect normal users

        else:
            messages.error(request, "Invalid login credentials.")
            return redirect('users:user_login')

    return render(request, 'books/login.html')

def user_logout(request):
    logout(request)
    return redirect('/')

def register(request):
    if request.user.is_authenticated:
        return redirect('users:user-dashboard')
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
            return redirect("users:register")

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("users:register")

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
                reverse('users:verify-email', kwargs={'uidb64': uid, 'token': token})
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
            return redirect("users:user_login")  # Redirect to the login page

        except Exception as e:
            logger.error(f"Registration failed: {str(e)}")
            messages.error(request, "Registration failed. Please try again.")
            return redirect("users:register")

    # Render the registration form
    return render(request, "books/register.html")


        
    @action(detail=False, methods=['post'])
    def resend_verification_email(self, request):
            email = request.data.get('email')

            if not email:
                return Response({'detail': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response({'detail': 'User with this email does not exist.'}, status=status.HTTP_404_NOT_FOUND)

            # Check if the user is already verified
            if user.is_active:
                return Response({'detail': 'User is already verified.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Generate a new verification token
                uid = urlsafe_base64_encode(force_bytes(user.id))
                token = default_token_generator.make_token(user)

                # Build the verification link
                verification_link = request.build_absolute_uri(
                    reverse('users:verify-email', kwargs={'uidb64': uid, 'token': token})
                )

                # Render the email template
                email_subject = 'Resend Verification Email'
                email_body = render_to_string('users/resend_verification.html', {
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
                email.content_subtype = 'html'
                email.send()
                

                return Response({
                    'detail': 'Verification email sent successfully. Please check your email.'
                }, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f'Failed to resend verification email: {str(e)}')
                return Response({'detail': 'Failed to resend verification email. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
    
    
class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, uidb64, token):
        try:
            # Decode UID (user ID)
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)

            # Check if the token is valid
            if default_token_generator.check_token(user, token):
                if not user.is_active:
                    user.is_active = True
                    user.save()
                    # Redirect to a success page
                    messages.success(request, "✅ Email Already Verified")
                    return redirect('users:user_login')
                else:
                    # Redirect to a page indicating the email is already verified
                    messages.success(request, "Email Verified Successfully!")
                    return redirect('users:user_login')
            else:
                # Redirect to an error page for invalid tokens
                messages.error(request, "The verification link is invalid or has expired. Please request a new verification email.")
                return redirect('users:verification-error')

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # Redirect to an error page for invalid links
            return redirect('users:verification-error')
        
        


# Password Reset Request View
def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            try:
                user = User.objects.get(email=email)  # Query CustomUser model
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Debugging output for uid and token
                print(f"UID: {uid}, Token: {token}")

                # Ensure the correct use of reverse with uid and token
                reset_link = request.build_absolute_uri(
                    reverse("users:password_reset_confirm", kwargs={"uidb64": uid, "token": token})
                )

                # Debugging output for reset link
                print(f"Reset link: {reset_link}")

                # Prepare email content
                email_subject = "Password Reset Request"
                email_body = render_to_string("users/password_reset_email.html", {
                    "user": user,
                    "domain": request.get_host(),
                    "protocol": "https" if request.is_secure() else "http",
                    "uidb64": uid,
                    "token": token,
                    "reset_link": reset_link,  # Pass the reset link to the template
                })

                # Send email
                email = EmailMessage(
                    email_subject,
                    email_body,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                )
                email.content_subtype = 'html'
                email.send()

                messages.success(request, "Password reset link has been sent to your email.")
            except User.DoesNotExist:
                messages.error(request, "No user found with this email.")

            return redirect("users:password_reset")  # Ensure correct namespace

    else:
        form = PasswordResetForm()

    return render(request, "users/password_reset_form.html", {"form": form})



# Password Reset Done View
def password_reset_done(request):
    return render(request, "users/password_reset_done.html")


def password_reset_confirm(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None

    if user and default_token_generator.check_token(user, token):
        if request.method == "POST":
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Your password has been successfully reset.")
                return redirect("users:password_reset_complete")  # Ensure namespace is correct
        else:
            form = SetPasswordForm(user)

        return render(request, "users/password_reset_confirm.html", {"form": form})

    messages.error(request, "The password reset link is invalid or has expired.")
    return redirect("users:password_reset")


# Password Reset Complete View
def password_reset_complete(request):
    return redirect(reverse('books:user_login'))





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
        return redirect('users:view-profile')  # Adjust this to your actual view

    # Pass profile and user data to the template
    return render(request, 'books/edit-profile.html', {'profile': profile, 'user': user})

