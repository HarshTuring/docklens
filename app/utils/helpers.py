import os
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, send_file
from PIL import Image

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