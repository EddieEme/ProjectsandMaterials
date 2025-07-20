from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework import routers
from . import views
from books.api_views import most_viewed_videos
from .utils import serve_preview, download_book





app_name = 'books'

# Router for API viewsets
router = routers.DefaultRouter()

# Web interface URLs
web_urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('resources/', views.resources, name='resources'),
    path('projects/', views.projects, name='projects'),
    path('project-list/', views.projectList, name='project-list'),
    path('product-details/<int:id>/', views.product_details, name='product-details'),
    path("category/<int:category_id>/", views.category_books, name="category_books"),
    path('faculty/<int:book_type_id>/', views.faculty, name='faculty'),
    path('payment-method/<int:id>/', views.payment_method, name='payment-method'),
    path('payment-checkout/', views.payment_checkout, name='payment-checkout'),
    path('login-projects/', views.login_projects, name='login-projects'),
    path('login-project-list/', views.login_projectList, name='login-project-list'),
    path('login-product-details/<int:id>/', views.login_product_details, name='login-product-details'),
    path('login-payment-method/', views.login_payment_method, name='login-payment-method'),
    path('verification-error/', views.verification_error, name='verification-error'),
    path('upload-book/', views.upload_book, name='upload-book'),
    path('download/<uuid:token>/', download_book, name='download-book'),
    
]

# API authentication URLs
auth_patterns = [
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    # path('api/most-viewed-videos/<str:channel_id>/', MostViewedVideos.as_view(), name='most-viewed-videos'),
    path('api/most-viewed-videos/<str:channel_id>/', most_viewed_videos, name='most-viewed-videos'),
    path("preview/<int:book_id>/", serve_preview, name="preview"),
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
]