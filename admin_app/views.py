import os
import re
import csv
import logging
from pathlib import Path, PureWindowsPath
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from google.cloud import storage
from books.models import Book, BookType, Category
from admin_app.models import AdminLog

logger = logging.getLogger(__name__)

# GCS Configuration
BUCKET_NAME = "projectsandmaterials_bucket"
BOOKS_FOLDER = "book_files/"
COVERS_FOLDER = "book_covers/"
client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def convert_windows_to_linux_path(windows_path):
    """Convert Windows path to Linux-compatible path"""
    try:
        # Normalize Windows path (handle both \ and /)
        windows_path = windows_path.replace('\\', '/')
        
        # Handle drive letters (C:/ → /mnt/c/)
        if re.match(r'^[A-Za-z]:/', windows_path):
            drive = windows_path[0].lower()
            return f"/mnt/{drive}/{windows_path[3:]}"
        
        # Handle network paths (\\server\share → /mnt/server/share)
        if windows_path.startswith('//'):
            return f"/mnt/{windows_path[2:].replace('/', '/')}"
            
        return windows_path
    except Exception as e:
        logger.error(f"Path conversion failed: {str(e)}")
        return None

def validate_and_convert_path(file_path):
    """Validate path exists and convert Windows paths if needed"""
    try:
        # First try direct path
        if os.path.exists(file_path):
            return file_path, None
            
        # Try converting Windows path if on Linux
        converted_path = convert_windows_to_linux_path(file_path)
        if converted_path and os.path.exists(converted_path):
            return converted_path, None
            
        return None, f"File not found at {file_path} or {converted_path}"
    except Exception as e:
        return None, f"Path validation error: {str(e)}"

def upload_to_gcs(local_path, destination_folder):
    """Upload file to GCS and return the relative path"""
    try:
        # Validate and convert path
        valid_path, error = validate_and_convert_path(local_path)
        if not valid_path:
            return None, error
            
        file_name = os.path.basename(valid_path)
        blob_path = f"{destination_folder}{file_name}"
        blob = bucket.blob(blob_path)
        
        blob.upload_from_filename(valid_path)
        
        # Return just the blob path, not full URL
        return blob_path, None
        
    except Exception as e:
        logger.error(f"GCS upload failed: {str(e)}")
        return None, f"Upload failed: {str(e)}"

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
                    
                    if not title or not file_path:
                        errors.append(f"Row {row_num}: Missing title or file_path")
                        continue

                    if Book.objects.filter(title__iexact=title).exists():
                        errors.append(f"Row {row_num}: Book '{title}' already exists")
                        continue

                    # Upload book file
                    book_url, error = upload_to_gcs(file_path, BOOKS_FOLDER)
                    if error:
                        errors.append(f"Row {row_num}: {error}")
                        continue

                    # Create book record
                    Book.objects.create(
                        title=title,
                        description=row.get("description", "").strip(),
                        author=row.get("author", "").strip(),
                        book_type=BookType.objects.get_or_create(name=row.get("book_type", "").strip())[0],
                        category=Category.objects.get_or_create(
                            name=row.get("category", "").strip(),
                            book_type=BookType.objects.get_or_create(name=row.get("book_type", "").strip())[0]
                        )[0],
                        price=5000,
                        file=book_url,
                        is_approved=row.get("is_approved", "False").lower() == "true",
                        user=request.user
                    )
                    success_count += 1

                except Exception as e:
                    errors.append(f"Row {row_num}: Error - {str(e)}")
                    logger.error(f"Row {row_num} error: {str(e)}")

            if success_count:
                AdminLog.objects.create(
                    user=request.user,
                    action=f"Batch uploaded {success_count} book(s)"
                )

            return JsonResponse({
                "success": bool(success_count),
                "message": f"Uploaded {success_count} books, {len(errors)} errors",
                "errors": errors
            })

        except Exception as e:
            logger.error(f"CSV processing failed: {str(e)}")
            return JsonResponse({
                "success": False,
                "message": f"Failed to process CSV: {str(e)}"
            }, status=500)

    return render(request, "admin_app/batch_upload_books.html")