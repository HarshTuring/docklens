import os
import uuid
import requests
from io import BytesIO
import re
from werkzeug.utils import secure_filename
from flask import current_app, send_file
from PIL import Image
from app.services.mongodb_service import ImageMetadataService

def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file):
    """Save the uploaded file with a unique name."""
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)

        ImageMetadataService.save_upload_metadata(
            filename=unique_filename,
            file_path=file_path,
            original_filename=file.filename,
            source_type="upload"
        )
        
        return unique_filename, file_path
    
    return None, None

def get_image_response(image_path):
    """
    Create a file response for an image.
    
    Args:
        image_path: Path to the image
        
    Returns:
        Response: Flask response with the image
    """
    try:
        # Get the image format
        img = Image.open(image_path)
        img_format = img.format.lower()
        mime_type = f"image/{img_format}"
        
        return send_file(image_path, mimetype=mime_type)
    except Exception as e:
        current_app.logger.error(f"Error creating image response: {str(e)}")
        return None
        
def is_valid_image_url(url):
    """
    Validate if a URL points to an image.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid and points to an image
    """
    # Basic URL validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # or ipv4
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        return False
    
    # Check content type to ensure it's an image
    try:
        response = requests.head(url, timeout=5)
        content_type = response.headers.get('Content-Type', '')
        return content_type.startswith('image/')
    except requests.RequestException:
        return False

def download_image_from_url(url):
    """
    Download an image from a URL and save it locally.
    
    Args:
        url: The URL of the image
        
    Returns:
        tuple: (filename, file_path) or (None, None) if download fails
    """

    already_processed, existing_record = ImageMetadataService.is_url_processed(url)

    if already_processed:
        # If the image was already downloaded before, check if file still exists
        file_path = existing_record.get('file_path')
        if file_path and os.path.exists(file_path):
            # Return the existing file
            return existing_record.get('filename'), file_path

    try:
        # Download the image
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for bad status codes
        
        # Check content type
        content_type = response.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            current_app.logger.error(f"URL does not point to an image: {url}")
            return None, None
        
        # Extract extension from content type
        extension = content_type.split('/')[-1]
        if extension == 'jpeg':
            extension = 'jpg'
        
        # Create a unique filename
        filename = f"url_image_{uuid.uuid4().hex}.{extension}"
        
        # Save to uploads directory
        upload_folder = current_app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        
        # Save the image
        with open(file_path, 'wb') as f:
            f.write(response.content)

        ImageMetadataService.save_upload_metadata(
            filename=filename,
            file_path=file_path,
            original_filename=filename,
            source_type="url",
            source_url=url
        )
        
        return filename, file_path
    except requests.RequestException as e:
        current_app.logger.error(f"Error downloading image from URL: {str(e)}")
        return None, None