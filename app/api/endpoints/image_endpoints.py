from flask import Blueprint, request, jsonify, current_app
from app.utils.helpers import (
    save_uploaded_file, 
    get_image_response, 
    is_valid_image_url, 
    download_image_from_url
)
from app.core.image_processor import process_image, convert_to_grayscale

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

@image_bp.route('/grayscale', methods=['POST'])
def grayscale_image():
    """
    Convert uploaded image to grayscale and return the processed image.
    
    Data flow:
    1. Upload the image
    2. Process image (convert to grayscale)
    3. Return processed image directly
    """
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Save the file if it's allowed
    _, file_path = save_uploaded_file(file)
    
    if not file_path:
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Convert to grayscale
    processed_path = convert_to_grayscale(file_path)
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/grayscale-url', methods=['POST'])
def grayscale_image_from_url():
    """
    Convert image from URL to grayscale and return the processed image.
    
    Data flow:
    1. Download image from URL
    2. Process image (convert to grayscale)
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg"
    }
    """
    # Get URL from request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    image_url = data['url']
    
    # Validate URL
    if not is_valid_image_url(image_url):
        return jsonify({'error': 'Invalid image URL'}), 400
    
    # Download image from URL
    _, file_path = download_image_from_url(image_url)
    
    if not file_path:
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Convert to grayscale
    processed_path = convert_to_grayscale(file_path)
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500