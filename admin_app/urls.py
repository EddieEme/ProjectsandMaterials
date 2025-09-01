from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path("batch-upload/", views.batch_upload_books, name="batch-upload"),
    path("regenerate-previews/", views.regenerate_previews, name="regenerate_previews"),
    path("regenerate-previews-page/", views.regenerate_previews_page, name="regenerate_previews_page"),
]