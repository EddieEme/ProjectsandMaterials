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

            for row_num, row in enumerate(reader, start=1):
                try:
                    title = row.get("title", "").strip()
                    file_path = row.get("file_path", "").strip()
                    book_type_name = row.get("book_type", "").strip()
                    category_name = row.get("category", "").strip()

                    # Validate required fields
                    if not title or not file_path or not book_type_name or not category_name:
                        errors.append(f"Row {row_num}: Missing required fields (title, file_path, book_type, category)")
                        continue

                    if Book.objects.filter(title__iexact=title).exists():
                        errors.append(f"Row {row_num}: Book '{title}' already exists")
                        continue

                    if not gcs_blob_exists(file_path):
                        errors.append(f"Row {row_num}: GCS file '{file_path}' does not exist")
                        continue

                    # Get or create book type
                    book_type, _ = BookType.objects.get_or_create(name=book_type_name)

                    # Get or create category and link to book type
                    try:
                        category, created = Category.objects.get_or_create(
                            name=category_name,
                            defaults={"book_type": book_type}
                        )
                        if not created and category.book_type != book_type:
                            category.book_type = book_type
                            category.save()
                    except Category.MultipleObjectsReturned:
                        errors.append(f"Row {row_num}: Duplicate category name found.")
                        continue
                    except Exception as e:
                        logger.exception(f"Row {row_num}: Failed to get or create category.")
                        errors.append(f"Row {row_num}: Error creating category - {str(e)}")
                        continue

                    # Create Book
                    Book.objects.create(
                        title=title,
                        description=row.get("description", "").strip(),
                        author=row.get("author", "").strip(),
                        book_type=book_type,
                        category=category,
                        price=5000,
                        file=file_path,
                        is_approved=row.get("is_approved", "False").strip().lower() == "true",
                        user=request.user
                    )

                    success_count += 1

                except Exception as e:
                    logger.exception(f"Row {row_num}: Unexpected error")
                    errors.append(f"Row {row_num}: Unexpected error - {str(e)}")

            # Log admin activity
            if success_count > 0:
                AdminLog.objects.create(
                    user=request.user,
                    action=f"Batch uploaded {success_count} book(s)"
                )

            return JsonResponse({
                "success": success_count > 0,
                "message": f"Uploaded {success_count} book(s), with {len(errors)} error(s)",
                "errors": errors
            })

        except Exception as e:
            logger.exception("Failed to process CSV file")
            return JsonResponse({
                "success": False,
                "message": f"Failed to process CSV file: {str(e)}"
            }, status=500)

    return render(request, "admin_app/batch_upload_books.html")
