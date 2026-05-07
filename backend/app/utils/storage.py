"""
backend/app/utils/storage.py
────────────────────────────
Utility functions for interacting with Supabase Storage.
"""

import os
from supabase import create_client, Client
from config import Config

# Initialize Supabase Client
supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)


def _bucket_candidates(configured_bucket: str | None = None) -> list[str]:
    configured = (configured_bucket or Config.SUPABASE_DOCUMENTS_BUCKET or "documents").strip()
    candidates = [configured, configured.lower(), configured.capitalize(), "Documents", "documents"]
    return list(dict.fromkeys(candidate for candidate in candidates if candidate))


def _bucket_names_from_response(response) -> list[str]:
    names: list[str] = []
    for bucket in response or []:
        if isinstance(bucket, dict):
            name = bucket.get("name") or bucket.get("id")
        else:
            name = getattr(bucket, "name", None) or getattr(bucket, "id", None)
        if name:
            names.append(str(name))
    return names


def _known_bucket_names() -> list[str]:
    try:
        return _bucket_names_from_response(supabase.storage.list_buckets())
    except Exception:
        return []


def _is_bucket_not_found(exc: Exception) -> bool:
    message = str(exc).lower()
    return "bucket not found" in message or "'statuscode': 400" in message


def public_storage_url(bucket_name: str, filename: str) -> str:
    base_url = Config.SUPABASE_URL.rstrip("/")
    safe_filename = filename.lstrip("/")
    return f"{base_url}/storage/v1/object/public/{bucket_name}/{safe_filename}"


def profile_photo_url(filename: str = "avatar.png") -> str:
    return public_storage_url(Config.SUPABASE_PROFILES_BUCKET, filename)


def logo_url(filename: str = "logo_enset.png") -> str:
    return public_storage_url(Config.SUPABASE_LOGOS_BUCKET, filename)


def upload_to_supabase_bucket(file_path: str, filename: str, bucket_name: str) -> str:
    with open(file_path, "rb") as f:
        file_data = f.read()

    last_error: Exception | None = None
    for candidate in _bucket_candidates(bucket_name):
        try:
            supabase.storage.from_(candidate).upload(
                file=file_data,
                path=filename,
                file_options={"cache-control": "3600", "upsert": "true"}
            )
            return supabase.storage.from_(candidate).get_public_url(filename)
        except Exception as e:
            last_error = e
            if not _is_bucket_not_found(e):
                print(f"Error uploading {filename} to Supabase bucket '{candidate}': {str(e)}")
                raise

    known = _known_bucket_names()
    tried = _bucket_candidates(bucket_name)
    hint = f" Available buckets: {', '.join(known)}." if known else ""
    print(
        f"Error uploading {filename} to Supabase: bucket not found. "
        f"Tried: {', '.join(tried)}.{hint}"
    )
    if last_error:
        raise last_error
    raise RuntimeError("Supabase bucket not found")

def upload_document_to_supabase(file_path: str, filename: str) -> str:
    """
    Uploads a local file to the Supabase Storage bucket.
    
    Args:
        file_path (str): The local path to the file (e.g. '../storage/documents/my_pdf.pdf')
        filename (str): The name to save the file as in the bucket (e.g. 'my_pdf.pdf')
        
    Returns:
        str: The public URL of the uploaded file.
    """
    return upload_to_supabase_bucket(file_path, filename, Config.SUPABASE_DOCUMENTS_BUCKET)


def upload_profile_photo_to_supabase(file_path: str, filename: str) -> str:
    return upload_to_supabase_bucket(file_path, filename, Config.SUPABASE_PROFILES_BUCKET)


def upload_logo_to_supabase(file_path: str, filename: str) -> str:
    return upload_to_supabase_bucket(file_path, filename, Config.SUPABASE_LOGOS_BUCKET)
