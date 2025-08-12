from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from . views import EmailVerificationView, CustomSocialSignupView

app_name = 'users'

urlpatterns = [
    path('user_login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='user_logout'),
    path('register/', views.register, name='register'),
    path('verify-email/<str:uidb64>/<str:token>/', EmailVerificationView.as_view(), name='verify-email'),
    path("accounts/password-reset/", views.password_reset_request, name="password_reset"),
    path("password-reset/done/", views.password_reset_done, name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("reset/done/", views.password_reset_complete, name="password_reset_complete"),
    
    path('user-settings/', views.user_settings, name='user-settings'),
    path('user-dashboard/', views.user_dashboard, name='user-dashboard'),
    path('view-profile/', views.view_profile, name='view-profile'),
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    
    path("accounts/social/signup/", CustomSocialSignupView.as_view(), name="socialaccount_signup"),
]