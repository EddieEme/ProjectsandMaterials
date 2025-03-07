from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import routers
from users.views import UserViewSet, AuthViewSet, EmailVerificationView
from . import views
from books.api_views import most_viewed_videos, GetDepartmentView, DepartmentAPIView
from .utils import extract_first_10_pages, serve_preview, download_book
from .payment import pay_with_paystack, pay_with_flutterwave, paystack_callback, flutterwave_callback


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
    path('departments/<int:category_id>/', views.department, name='departments'),
    path('payment-method/<int:id>/', views.payment_method, name='payment-method'),
    path('payment-checkout/', views.payment_checkout, name='payment-checkout'),
    path('subscription/', views.subscription, name='subscription'),
    path('buyorsubscribe/<int:id>/', views.buyorsubscribe, name='buyorsubscribe'),
    path('login-projects/', views.login_projects, name='login-projects'),
    path('login-project-list/', views.login_projectList, name='login-project-list'),
    path('login-product-details/<int:id>/', views.login_product_details, name='login-product-details'),
    path('login-departments/<int:category_id>/', views.login_department, name='login-departments'),
    path('login-payment-method/', views.login_payment_method, name='login-payment-method'),
    path('login-subscription/', views.login_subscription, name='login-subscription'),
    path('login-buyorsubscribe/<int:id>/', views.login_buyorsubscribe, name='login-buyorsubscribe'),
    path('login-home/', views.login_home, name='login-home'),
    path('verify-email/<str:uidb64>/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path('verification-error/', views.verification_error, name='verification-error'),
    path('user-settings/', views.user_settings, name='user-settings'),
    path('user-dashboard/', views.user_dashboard, name='user-dashboard'),
    path('view-profile/', views.view_profile, name='view-profile'),
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    path('download/<uuid:token>/', download_book, name='download_book'),
]

# API authentication URLs
auth_patterns = [
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/get-categories/', GetDepartmentView.as_view(), name='get-categories'),
    path('api/department/<int:category_id>/', DepartmentAPIView.as_view(), name='api-department'),
    path('api/auth/resend-verification-email/', AuthViewSet.as_view({'post': 'resend_verification_email'}), name='resend-verification-email'),
    # path('api/most-viewed-videos/<str:channel_id>/', MostViewedVideos.as_view(), name='most-viewed-videos'),
    path('api/most-viewed-videos/<str:channel_id>/', most_viewed_videos, name='most-viewed-videos'),
    path("preview/<int:book_id>/", serve_preview, name="preview"),
]

payment_patterns = [
    path('paystack/<int:book_id>/', pay_with_paystack, name='pay_with_paystack'),
    path('flutterwave/<int:book_id>/', pay_with_flutterwave, name='pay_with_flutterwave'),
    path('paystack/callback/', paystack_callback, name='paystack_callback'),
    path('flutterwave/callback/', flutterwave_callback, name='flutterwave_callback'),
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
    *api_urlpatterns, 
    *payment_patterns,
]