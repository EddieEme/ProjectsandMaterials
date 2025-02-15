from django.urls import path
from django.contrib.auth import views as auth_views
from .views import *

app_name = 'users'

urlpatterns = [
    path("accounts/password-reset/", password_reset_request, name="password_reset"),
    path("password-reset/done/", password_reset_done, name="password_reset_done"),
    path("password-reset-confirm/<uidb64>/<token>/", password_reset_confirm, name="password_reset_confirm"),
    path("reset/done/", password_reset_complete, name="password_reset_complete"),
]