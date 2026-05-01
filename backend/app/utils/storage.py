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

def upload_document_to_supabase(file_path: str, filename: str) -> str:
    """
    Uploads a local file to the Supabase Storage bucket.
    
    Args:
        file_path (str): The local path to the file (e.g. '../storage/documents/my_pdf.pdf')
        filename (str): The name to save the file as in the bucket (e.g. 'my_pdf.pdf')
        
    Returns:
        str: The public URL of the uploaded file.
    """
    bucket_name = Config.SUPABASE_BUCKET
    
    # Read the file as binary
    with open(file_path, "rb") as f:
        file_data = f.read()
        
    # Upload to Supabase (upsert=True will overwrite if file exists with same name)
    try:
        response = supabase.storage.from_(bucket_name).upload(
            file=file_data,
            path=filename,
            file_options={"cache-control": "3600", "upsert": "true"}
        )
        
        # Get the public URL
        public_url = supabase.storage.from_(bucket_name).get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"Error uploading {filename} to Supabase: {str(e)}")
        raise e
