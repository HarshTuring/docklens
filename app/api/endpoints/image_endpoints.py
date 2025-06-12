from flask import Blueprint, request, jsonify, current_app
from app.utils.helpers import save_uploaded_file
from app.core.image_processor import process_image

image_bp = Blueprint('image', __name__)

@image_bp.route('/upload', methods=['POST'])
def upload_image():
    """Handle image upload via POST request."""
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save the file if it's allowed
    filename, file_path = save_uploaded_file(file)
    
    if filename:
        # Process the image (placeholder for now)
        result = process_image(file_path)
        
        return jsonify({
            'message': 'Image successfully uploaded',
            'filename': filename,
            'processing': result
        }), 200
    
    return jsonify({'error': 'File type not allowed'}), 400