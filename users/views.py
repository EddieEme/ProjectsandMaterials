from rest_framework.authtoken.models import Token
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
from .serializers import *

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
        profile, created = Profile.objects.get_or_create(user=user)

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
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    def get_serializer_class(self):
        """Return appropriate serializer for each action."""
        if self.action == 'register':
            return RegisterSerializer
        elif self.action == 'login':
            return LoginSerializer
        return self.serializer_class

    @action(detail=False, methods=['post'])
    def register(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        # Validate email before creating user
        try:
            validate_email(data['email'])
        except ValidationError:
            return Response({'detail': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=data['email']).exists():
            return Response({'detail': 'Email already exists'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Generate email verification token
            uid = urlsafe_base64_encode(force_bytes(data['email']))
            token = default_token_generator.make_token(User(email=data['email']))

            verification_link = request.build_absolute_uri(
                reverse('verify-email', kwargs={'uidb64': uid, 'token': token})
            )

            # Send verification email
            send_mail(
                'Verify Your Email',
                f'Click the link to verify your email: {verification_link}',
                settings.DEFAULT_FROM_EMAIL,
                [data['email']],
                fail_silently=False,
            )

            # If everything succeeds, create the user
            user = User.objects.create_user(**data, is_active=False)  # Mark inactive until email verified

            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'detail': 'User registered successfully. Please check your email for verification.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'detail': f'Registration failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
    @action(detail=False, methods=['post'])
    def login(self, request):
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            user = authenticate(email=data['email'], password=data['password'])

            if not user:
                return Response(
                    {'detail': 'Invalid email or password'}, 
                    status=status.HTTP_401_UNAUTHORIZED
                )

            if not user.is_active:
                return Response(
                    {'detail': 'Account is disabled'}, 
                    status=status.HTTP_403_FORBIDDEN
                )

            # Generate JWT Tokens
            refresh = RefreshToken.for_user(user)

            return Response({
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'profile': {
                        'id': user.profile.id,
                        'bio': user.profile.bio,
                        'profession': user.profile.profession,
                        'phone_number': user.profile.phone_number,
                        'can_publish': user.profile.can_publish,
                        'created_at': user.profile.created_at
                    }
                }
            }, status=status.HTTP_200_OK)
    
    
@api_view(['GET'])
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, id=uid)

        if default_token_generator.check_token(user, token):
            user.is_active = True  # Activate the account
            user.save()
            return Response({'detail': 'Email verified successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Invalid or expired token'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'detail': 'Invalid request'}, status=status.HTTP_400_BAD_REQUEST)