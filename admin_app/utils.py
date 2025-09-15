import os
from django.core.files.storage import default_storage
from google.cloud import storage

# Google Cloud Storage Setup
BUCKET_NAME = "projectsandmaterials_bucket"
BOOKS_FOLDER = "book_files/"
COVERS_FOLDER = "book_covers/"

client = storage.Client()
bucket = client.bucket(BUCKET_NAME)

def upload_to_gcs(local_path, destination_folder, content_type=None, public=False):
    """
    Uploads a file to Google Cloud Storage.
    
    Args:
        local_path: Path to local file
        destination_folder: Target folder in GCS
        content_type: Explicit content type
        public: Whether to make file publicly accessible
    
    Returns:
        tuple: (gcs_url, error_message)
    """
    is_valid, error_msg = validate_file(local_path, ALLOWED_FILE_TYPES.keys())
    if not is_valid:
        return None, error_msg

    try:
        file_name = os.path.basename(local_path)
        blob_path = f"{destination_folder}{file_name}"
        blob = bucket.blob(blob_path)
        
        if content_type is None:
            content_type, _ = mimetypes.guess_type(local_path)
            if not content_type:
                content_type = ALLOWED_FILE_TYPES.get(Path(local_path).suffix.lower())
        
        blob.content_type = content_type or 'application/octet-stream'
        blob.upload_from_filename(local_path)
        
        if public:
            blob.make_public()
            # Return the direct public URL
            return f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_path}", None
        else:
            # For private files, return just the blob path (not gs:// URI)
            return blob_path, None
        
    except GoogleCloudError as e:  # pyright: ignore[reportUndefinedVariable]
        logger.error(f"GCS upload error: {str(e)}")
        return None, f"Google Cloud Storage error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        return None, f"Unexpected error uploading file: {str(e)}"