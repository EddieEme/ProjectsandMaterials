from background_task import background
from books.models import Book
from books.utils import generate_preview
import logging
from celery import shared_task

logger = logging.getLogger(__name__)

@background(schedule=5)  # Runs 5 seconds later
@shared_task
def generate_preview_task(book_id):
    try:
        book = Book.objects.get(id=book_id)
        from .utils import generate_preview
        preview_url = generate_preview(book)
        if preview_url:
            book.preview_url = preview_url
            book.save(update_fields=['preview_url'])
    except Exception as e:
        logger.error(f"Failed to generate preview for book {book_id}: {e}")