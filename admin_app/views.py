import os
import csv
import logging
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from google.cloud import storage
from books.models import Book, BookType, Category
from admin_app.models import AdminLog
from django.conf import settings
from books.utils import generate_preview_task
from django.db import transaction

logger = logging.getLogger(__name__)

# GCS Setup
BUCKET_NAME = "projectsandmaterials_bucket"
BOOKS_FOLDER = "book_files/"
client = storage.Client(credentials=settings.GS_CREDENTIALS)
bucket = client.bucket(BUCKET_NAME)

def gcs_blob_exists(gcs_path):
    """Check if a GCS blob exists"""
    try:
        blob = bucket.blob(gcs_path)
        return blob.exists()
    except Exception as e:
        logger.error(f"GCS check failed for '{gcs_path}': {e}")
        return False



@login_required
@user_passes_test(lambda u: u.is_superuser)
def batch_upload_books(request):
    if request.method == "POST":
        csv_file = request.FILES.get("file")

        if not csv_file or not csv_file.name.endswith('.csv'):
            return JsonResponse({
                "success": False,
                "message": "Please upload a valid CSV file"
            }, status=400)

        try:
            decoded_file = csv_file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)

            errors = []
            success_count = 0
            preview_errors = []
            
            # Initialize GCS client once
            client = storage.Client(credentials=settings.GS_CREDENTIALS)
            bucket = client.bucket(settings.GS_BUCKET_NAME)
            preview_bucket = client.bucket("preview_projectandmaterials")

            for row_num, row in enumerate(reader, start=1):
                try:
                    with transaction.atomic():
                        title = row.get("title", "").strip()
                        file_path = row.get("file_path", "").strip()
                        book_type_name = row.get("book_type", "").strip()
                        category_name = row.get("category", "").strip()

                        # Validate required fields
                        if not all([title, file_path, book_type_name, category_name]):
                            errors.append(f"Row {row_num}: Missing required fields")
                            continue

                        if Book.objects.filter(title__iexact=title).exists():
                            errors.append(f"Row {row_num}: Book '{title}' already exists")
                            continue

                        # Verify GCS file exists
                        try:
                            if not bucket.blob(file_path).exists():
                                errors.append(f"Row {row_num}: GCS file '{file_path}' does not exist")
                                continue
                        except Exception as e:
                            errors.append(f"Row {row_num}: GCS error - {str(e)}")
                            continue

                        # Get or create book type and category
                        book_type, _ = BookType.objects.get_or_create(name=book_type_name)
                        category, _ = Category.objects.get_or_create(
                            name=category_name,
                            defaults={"book_type": book_type}
                        )

                        # Create book record
                        book = Book.objects.create(
                            title=title,
                            description=row.get("description", ""),
                            author=row.get("author", "").strip(),
                            book_type=book_type,
                            category=category,
                            price=5000,
                            file=file_path,
                            is_approved=row.get("is_approved", "False").strip().lower() == "true",
                            user=request.user
                        )

                        # Generate preview synchronously with error handling
                        try:
                            preview_url = generate_preview_task(book.id)
                            if preview_url:
                                book.preview_url = preview_url
                                book.save(update_fields=['preview_url'])
                            else:
                                preview_errors.append(f"Row {row_num}: Preview generation failed")
                        except Exception as e:
                            logger.error(f"Preview generation failed for book {book.id}: {e}")
                            preview_errors.append(f"Row {row_num}: Preview generation error")

                        success_count += 1

                except Exception as e:
                    logger.exception(f"Row {row_num}: Unexpected error")
                    errors.append(f"Row {row_num}: Error - {str(e)}")

            # Log admin activity
            if success_count > 0:
                AdminLog.objects.create(
                    user=request.user,
                    action=f"Batch uploaded {success_count} book(s)"
                )

            return JsonResponse({
                "success": success_count > 0,
                "message": f"Completed {success_count} book(s), {len(errors)} errors, {len(preview_errors)} preview errors",
                "errors": errors,
                "preview_errors": preview_errors
            })

        except Exception as e:
            logger.exception("CSV processing failed")
            return JsonResponse({
                "success": False,
                "message": f"System error: {str(e)}"
            }, status=500)

    return render(request, "admin_app/batch_upload_books.html")