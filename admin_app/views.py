from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
import csv
from books.models import Book, BookType, Category
from admin_app.models import AdminLog


def is_admin(user):
    """Check if the user is an admin."""
    return user.is_superuser

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    """Admin dashboard view."""
    return render(request, "admin_app/dashboard.html")

@login_required
@user_passes_test(is_admin)
def batch_upload_books(request):
    """Batch upload books via CSV."""
    if request.method == "POST":
        file = request.FILES.get("file")
        
        if not file or not file.name.endswith('.csv'):
            return JsonResponse({"success": False, "message": "Please upload a valid CSV file."}, status=400)
        
        try:
            decoded_file = file.read().decode('utf-8').splitlines()
            reader = csv.DictReader(decoded_file)
            
            errors = []  # To store errors for each row
            success_count = 0  # To count successfully uploaded books
            
            for row_num, row in enumerate(reader, start=1):
                title = row.get("title")
                description = row.get("description")
                author = row.get("author")
                book_type_name = row.get("book_type")
                category_name = row.get("category")
                file_path = row.get("file")
                cover_image_path = row.get("cover_image")

                # Check if a book with the same title already exists
                if Book.objects.filter(title__iexact=title).exists():
                    errors.append(f"Row {row_num}: A book with the title '{title}' already exists.")
                    continue

                # Validate file type
                if not file_path.lower().endswith(('.pdf', '.docx')):
                    errors.append(f"Row {row_num}: Invalid file type for '{file_path}'. Only PDF and DOCX files are allowed.")
                    continue

                # Handle book type (faculty)
                try:
                    book_type, _ = BookType.objects.get_or_create(name=book_type_name)
                except Exception as e:
                    errors.append(f"Row {row_num}: Error creating/retrieving book type '{book_type_name}': {str(e)}")
                    continue
                
                # Handle category (department)
                try:
                    category, _ = Category.objects.get_or_create(name=category_name, book_type=book_type)
                except Exception as e:
                    errors.append(f"Row {row_num}: Error creating/retrieving category '{category_name}': {str(e)}")
                    continue
                
                # Create the book
                try:
                    Book.objects.create(
                        title=title,
                        description=description,
                        author=author,
                        book_type=book_type,
                        category=category,
                        price=5000,  # Fixed price
                        file=file_path,
                        cover_image=cover_image_path,
                        user=request.user
                    )
                    success_count += 1
                except Exception as e:
                    errors.append(f"Row {row_num}: Error creating book '{title}': {str(e)}")
            
            # Log the action
            AdminLog.objects.create(
                user=request.user,
                action=f"Batch uploaded {success_count} book(s)."
            )
            
            # Return JSON response
            response_data = {
                "success": True,
                "message": f"Successfully uploaded {success_count} book(s).",
                "errors": errors
            }
            return JsonResponse(response_data)
        
        except Exception as e:
            return JsonResponse({"success": False, "message": f"Error processing CSV file: {str(e)}"}, status=500)
    
    # Render the batch upload template
    return render(request, "admin_app/batch_upload_books.html")