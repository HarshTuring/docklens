from flask import Blueprint, request, jsonify, current_app
from app.utils.helpers import (
    save_uploaded_file, 
    get_image_response, 
    is_valid_image_url, 
    download_image_from_url
)
from app.utils.logger import log_operation, get_operation_logs
from app.core.image_processor import process_image, convert_to_grayscale
from flasgger import swag_from

image_bp = Blueprint('image', __name__)

@image_bp.route('/upload', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Upload an image file",
    "description": "Upload an image file to the server",
    "consumes": ["multipart/form-data"],
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to upload",
            "required": True,
            "type": "file"
        }
    ],
    "responses": {
        "200": {
            "description": "Image successfully uploaded",
            "schema": {
                "$ref": "#/components/schemas/UploadResponse"
            }
        },
        "400": {
            "description": "Bad request",
            "schema": {
                "$ref": "#/components/schemas/Error"
            }
        }
    }
})
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
        # Log the upload operation
        log_operation(
            image_name=filename,
            operation="upload",
            source_type="upload",
            details={"original_filename": file.filename, "saved_path": file_path}
        )
        
        # Process the image (placeholder for now)
        result = process_image(file_path)
        
        return jsonify({
            'message': 'Image successfully uploaded',
            'filename': filename,
            'processing': result
        }), 200
    
    # Log failed upload
    log_operation(
        image_name=file.filename if file.filename else "unknown",
        operation="upload",
        source_type="upload",
        status="error",
        details={"error": "File type not allowed"}
    )
    
    return jsonify({'error': 'File type not allowed'}), 400

@image_bp.route('/grayscale', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Convert uploaded image to grayscale",
    "description": "Upload an image and convert it to grayscale. Returns the processed image directly.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to convert to grayscale",
            "required": True,
            "type": "file"
        }
    ],
    "responses": {
        "200": {
            "description": "Grayscale image",
            "content": {
                "image/*": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        "400": {
            "description": "Bad request",
            "schema": {
                "$ref": "#/components/schemas/Error"
            }
        },
        "500": {
            "description": "Processing error",
            "schema": {
                "$ref": "#/components/schemas/Error"
            }
        }
    }
})
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
    filename, file_path = save_uploaded_file(file)
    
    if not file_path:
        # Log failed upload
        log_operation(
            image_name=file.filename if file.filename else "unknown",
            operation="grayscale",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_grayscale",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Convert to grayscale
    processed_path = convert_to_grayscale(file_path, source_type="upload")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/grayscale-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Convert image from URL to grayscale",
    "description": "Fetch an image from the provided URL and convert it to grayscale. Returns the processed image directly.",
    "consumes": ["application/json"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image to convert",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Grayscale image",
            "content": {
                "image/*": {
                    "schema": {
                        "type": "string",
                        "format": "binary"
                    }
                }
            }
        },
        "400": {
            "description": "Bad request or invalid URL",
            "schema": {
                "$ref": "#/components/schemas/Error"
            }
        },
        "500": {
            "description": "Processing error",
            "schema": {
                "$ref": "#/components/schemas/Error"
            }
        }
    }
})
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
        # Log invalid URL
        log_operation(
            image_name="unknown",
            operation="grayscale",
            source_type="url",
            status="error",
            details={"error": "Invalid image URL", "url": image_url}
        )
        return jsonify({'error': 'Invalid image URL'}), 400
    
    # Download image from URL
    filename, file_path = download_image_from_url(image_url)
    
    if not file_path:
        # Log download failure
        log_operation(
            image_name="unknown",
            operation="grayscale",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_grayscale",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Convert to grayscale
    processed_path = convert_to_grayscale(file_path, source_type="url")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/logs', methods=['GET'])
@swag_from({
    "tags": ["Logs"],
    "summary": "Get operation logs",
    "description": "Retrieve logs of image processing operations with optional filtering",
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "limit",
            "in": "query",
            "description": "Maximum number of logs to return",
            "required": False,
            "type": "integer",
            "default": 100
        },
        {
            "name": "operation",
            "in": "query",
            "description": "Filter logs by operation type (e.g., 'upload', 'grayscale')",
            "required": False,
            "type": "string"
        },
        {
            "name": "source",
            "in": "query",
            "description": "Filter logs by source type (e.g., 'upload', 'url')",
            "required": False,
            "type": "string"
        }
    ],
    "responses": {
        "200": {
            "description": "List of operation logs",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "timestamp": {"type": "string"},
                        "unix_timestamp": {"type": "integer"},
                        "image_name": {"type": "string"},
                        "operation": {"type": "string"},
                        "source_type": {"type": "string"},
                        "status": {"type": "string"},
                        "details": {"type": "object"}
                    }
                }
            }
        }
    }
})
def get_logs():
    """Get operation logs with optional filtering."""
    # Parse query parameters
    limit = request.args.get('limit', default=100, type=int)
    operation = request.args.get('operation', default=None, type=str)
    source = request.args.get('source', default=None, type=str)
    
    # Get logs
    logs = get_operation_logs(limit=limit, operation_type=operation, source_type=source)
    
    return jsonify(logs), 200

@image_bp.route('/history', methods=['GET'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Get image processing history",
    "description": "Retrieve history of image uploads and processing from MongoDB",
    "produces": ["application/json"],
    "parameters": [
        {
            "name": "limit",
            "in": "query",
            "description": "Maximum number of records to return",
            "required": False,
            "type": "integer",
            "default": 10
        },
        {
            "name": "operation",
            "in": "query",
            "description": "Filter by operation type (e.g., 'grayscale')",
            "required": False,
            "type": "string"
        },
        {
            "name": "source",
            "in": "query",
            "description": "Filter by source type (e.g., 'upload', 'url')",
            "required": False,
            "type": "string"
        }
    ],
    "responses": {
        "200": {
            "description": "List of image processing history",
            "schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "upload_date": {"type": "string"},
                        "source_type": {"type": "string"},
                        "processed_images": {
                            "type": "array",
                            "items": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_image_history():
    """Get image processing history from MongoDB."""
    # Parse query parameters
    limit = request.args.get('limit', default=10, type=int)
    operation = request.args.get('operation', default=None, type=str)
    source = request.args.get('source', default=None, type=str)
    
    # Get history from MongoDB service
    from app.services.mongodb_service import ImageMetadataService
    history = ImageMetadataService.get_processing_history(
        limit=limit, 
        operation=operation, 
        source_type=source
    )
    
    # Format dates in the response
    for record in history:
        if 'upload_date' in record:
            record['upload_date'] = record['upload_date'].isoformat()
        if 'processed_images' in record:
            for img in record['processed_images']:
                if 'processed_date' in img:
                    img['processed_date'] = img['processed_date'].isoformat()
    
    return jsonify(history), 200