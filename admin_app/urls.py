from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path("batch-upload/", views.batch_upload_books, name="batch-upload"),
]