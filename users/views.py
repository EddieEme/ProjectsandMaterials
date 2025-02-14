from django.shortcuts import redirect, render
from rest_framework.authtoken.models import Token
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from django.contrib.auth import authenticate
from rest_framework.decorators import api_view
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import action, authentication_classes, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.views import APIView
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.contrib import messages

from .serializers import *

import logging

logger = logging.getLogger(__name__)

User = get_user_model() 


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Ensure users can only access their own profile"""
        return User.objects.filter(id=self.request.user.id)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Retrieve the currently authenticated user's details"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['put', 'patch'])
    @authentication_classes([JWTAuthentication])
    def update_profile(self, request):
        """Update both User and Profile in a single request"""
        user = request.user

        # Ensure user has a profile or create one
        profile, created = Profile.objects.get_or_create(user=user, defaults={'bio': '', 'profession': ''})

        # Extract profile data separately if sent under a "profile" key
        profile_data = request.data.get("profile", {})

        user_serializer = UserSerializer(user, data=request.data, partial=True)
        profile_serializer = ProfileSerializer(profile, data=profile_data, partial=True)

        if user_serializer.is_valid() and profile_serializer.is_valid():
            user_serializer.save()
            profile_serializer.save()

            return Response(
                {
                    "message": "Profile updated successfully",
                    "user": user_serializer.data,
                    "profile": profile_serializer.data
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "user_errors": user_serializer.errors,
                "profile_errors": profile_serializer.errors
            },
            status=status.HTTP_400_BAD_REQUEST
        )


class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]  # Allow any user to access these endpoints
    serializer_class = LoginSerializer  # Default serializer

    def get_serializer_class(self):
        """Return appropriate serializer for each action."""
        if self.action == 'register':
            return RegisterSerializer
        elif self.action == 'login':
            return LoginSerializer
        return self.serializer_class

    @action(detail=False, methods=['post'])
    def register(self, request):
        """Register a new user."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Check if email already exists
        if User.objects.filter(email=data['email']).exists():
            return Response({'detail': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create the user (inactive until email is verified)
            user = User.objects.create_user(**data, is_active=False)

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

            # Generate JWT tokens (for immediate login after registration)
            refresh = RefreshToken.for_user(user)

            # Set tokens as HTTP-only cookies
            response = Response({
                'detail': 'User registered successfully. Please check your email for verification.',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                }
            }, status=status.HTTP_201_CREATED)

            # Set access and refresh tokens as HTTP-only cookies
            response.set_cookie(
                key='access_token',
                value=str(refresh.access_token),
                httponly=True,
                secure=True,  # Only send over HTTPS
                samesite='Lax', # Prevent CSRF
                max_age=timedelta(minutes=15).total_seconds(),  # Short-lived access token
            )
            response.set_cookie(
                key='refresh_token',
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite='Lax',
                max_age=timedelta(days=7).total_seconds(),  # Longer-lived refresh token
            )

            return response

        except Exception as e:
            logger.error(f'Registration failed: {str(e)}')
            return Response({'detail': 'Registration failed. Please try again.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """Authenticate a user and return JWT tokens."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Authenticate the user
        user = authenticate(email=data['email'], password=data['password'])

        if not user:
            logger.warning(f"Failed login attempt for email: {data['email']}")
            return Response({'detail': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({'detail': 'Account is disabled'}, status=status.HTTP_403_FORBIDDEN)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Set tokens as HTTP-only cookies
        response = Response({
            'detail': 'Login successful',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            }
        }, status=status.HTTP_200_OK)

        response.set_cookie(
            key='access_token',
            value=str(refresh.access_token),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=timedelta(minutes=15).total_seconds(),  # Short-lived access token
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',
            max_age=timedelta(days=7).total_seconds(),  # Longer-lived refresh token
        )

        return response

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """Log out the user by clearing cookies."""
        response = Response({'detail': 'Logout successful'}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        return response

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Fetch the authenticated user's data."""
        user = request.user
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def logout(self, request):
        """
        Log out the user by clearing JWT cookies.
        """
        response = Response({'detail': 'Logout successful'}, status=status.HTTP_200_OK)
        
        # Clear access_token and refresh_token cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response
        
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
                    reverse('books:verify-email', kwargs={'uidb64': uid, 'token': token})
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
                    return redirect('books:user_login')
                else:
                    # Redirect to a page indicating the email is already verified
                    messages.success(request, "Email Verified Successfully!")
                    return redirect('books:user_login')
            else:
                # Redirect to an error page for invalid tokens
                messages.error(request, "The verification link is invalid or has expired. Please request a new verification email.")
                return redirect('books:verification-error')

        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            # Redirect to an error page for invalid links
            return redirect('books:verification-error')
        
        







