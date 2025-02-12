from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import routers
from users.views import UserViewSet, AuthViewSet, EmailVerificationView
from . import views


app_name = 'books'

# Router for API viewsets
router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename='users')
router.register(r'auth', AuthViewSet, basename='auth')

# Web interface URLs
web_urlpatterns = [
    path('', views.home, name='home'),
    path('projects/', views.projects, name='projects'),
    path('project-list/', views.projectList, name='project-list'),
    path('user_login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('register/', views.register, name='register'),
    path('product-details/<int:id>/', views.product_details, name='product-details'),
    path('departments/', views.department, name='departments'),
    path('payment-method/', views.payment_method, name='payment-method'),
    path('subscription/', views.subscription, name='subscription'),
    path('buyorsubscribe/', views.buyorsubscribe, name='buyorsubscribe'),
    path('login-projects/', views.login_projects, name='login-projects'),
    path('login-project-list/', views.login_projectList, name='login-project-list'),
    path('login-product-details/<int:id>/', views.login_product_details, name='login-product-details'),
    path('login-departments/', views.login_department, name='login-departments'),
    path('login-payment-method/', views.login_payment_method, name='login-payment-method'),
    path('login-subscription/', views.login_subscription, name='login-subscription'),
    path('login-buyorsubscribe/', views.login_buyorsubscribe, name='login-buyorsubscribe'),
    path('login-home/', views.login_home, name='login-home'),
    path('verify-email/<str:uidb64>/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('verification-success/', views.verification_success, name='verification-success'),
    path('verification-error/', views.verification_error, name='verification-error'),
    path('verification-already-done/', views.verification_already_done, name='verification-already-done'),
]

# API authentication URLs
auth_patterns = [
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/resend-verification-email/', AuthViewSet.as_view({'post': 'resend_verification_email'}), name='resend-verification-email'),
]

# API ViewSet URLs
api_urlpatterns = [
    path('api/', include(router.urls)),  # API ViewSets
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),  # Browsable API auth
]

# Combine all URL patterns
urlpatterns = [
    *web_urlpatterns,  # Web pages
    *auth_patterns,    # Authentication endpoints
    *api_urlpatterns,  # API ViewSets
]