from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path("batch-upload-books/", views.batch_upload_books, name="batch-upload-books"),
]