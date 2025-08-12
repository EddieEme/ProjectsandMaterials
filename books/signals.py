from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Book

@receiver(post_delete, sender=Book)
def delete_book_files(sender, instance, **kwargs):
    # Delete the cover image and book file from GCS
    instance.cover_image.delete(save=False)
    instance.file.delete(save=False)