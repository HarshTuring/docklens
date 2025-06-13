from flask import Blueprint, request, jsonify, current_app
from app.utils.helpers import (
    save_uploaded_file, 
    get_image_response, 
    is_valid_image_url, 
    download_image_from_url
)
from app.utils.logger import log_operation, get_operation_logs
from app.core.image_processor import process_image, convert_to_grayscale, apply_blur, rotate_image, resize_image, remove_background, apply_transformations
from flasgger import swag_from
from app.services.redis_service import ImageCacheService
import json

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

@image_bp.route('/cache/stats', methods=['GET'])
@swag_from({
    "tags": ["Cache Management"],
    "summary": "Get cache statistics",
    "description": "View statistics about the Redis image cache",
    "produces": ["application/json"],
    "responses": {
        "200": {
            "description": "Cache statistics",
            "schema": {
                "type": "object",
                "properties": {
                    "exact_hash_count": {"type": "integer"},
                    "perceptual_hash_count": {"type": "integer"},
                    "operations": {"type": "object"},
                    "memory_usage": {"type": "string"}
                }
            }
        }
    }
})
def get_cache_stats():
    """Get statistics about the Redis image cache."""
    redis_client = current_app.redis
    
    # Count exact hash keys
    exact_hash_keys = redis_client.keys(f"{ImageCacheService.EXACT_HASH_PREFIX}*")
    
    # Count entries in perceptual hash sorted sets
    phash_keys = redis_client.keys(f"{ImageCacheService.PHASH_PREFIX}*")
    phash_counts = {}
    total_phash_entries = 0
    
    for key in phash_keys:
        key_str = key.decode('utf-8')
        operation = key_str.replace(ImageCacheService.PHASH_PREFIX, '')
        count = redis_client.zcard(key)
        phash_counts[operation] = count
        total_phash_entries += count
    
    # Get Redis memory info
    info = redis_client.info('memory')
    
    return jsonify({
        "exact_hash_count": len(exact_hash_keys),
        "perceptual_hash_count": total_phash_entries,
        "operations": phash_counts,
        "memory_usage": info.get('used_memory_human', 'unknown'),
        "peak_memory": info.get('used_memory_peak_human', 'unknown')
    }), 200

@image_bp.route('/cache/clear', methods=['POST'])
@swag_from({
    "tags": ["Cache Management"],
    "summary": "Clear the image cache",
    "description": "Remove all cached image processing results from Redis",
    "produces": ["application/json"],
    "responses": {
        "200": {
            "description": "Cache cleared",
            "schema": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "message": {"type": "string"}
                }
            }
        }
    }
})
def clear_cache():
    """Clear the Redis image cache."""
    success = ImageCacheService.clear_cache()
    
    if success:
        return jsonify({
            "success": True,
            "message": "Image cache cleared successfully"
        }), 200
    else:
        return jsonify({
            "success": False,
            "message": "Error clearing cache"
        }), 500
    
@image_bp.route('/blur', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Apply blur filter to an uploaded image",
    "description": "Upload an image and apply a blur filter with specified radius. Returns the processed image directly.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to process",
            "required": True,
            "type": "file"
        },
        {
            "name": "radius",
            "in": "formData",
            "description": "Blur radius (larger values create stronger blur)",
            "required": False,
            "type": "number",
            "default": 2.0
        }
    ],
    "responses": {
        "200": {
            "description": "Blurred image",
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
def blur_image():
    """
    Apply blur filter to uploaded image and return the processed image.
    
    Data flow:
    1. Upload the image
    2. Process image (apply blur)
    3. Return processed image directly
    """
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get blur radius from form
    try:
        radius = float(request.form.get('radius', 2.0))
        if radius <= 0:
            return jsonify({'error': 'Blur radius must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid blur radius'}), 400
    
    # Save the file if it's allowed
    filename, file_path = save_uploaded_file(file)
    
    if not file_path:
        # Log failed upload
        log_operation(
            image_name=file.filename if file.filename else "unknown",
            operation=f"blur_{radius}",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_blur",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Apply blur
    processed_path = apply_blur(file_path, radius, source_type="upload")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500


@image_bp.route('/blur-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Apply blur filter to image from URL",
    "description": "Fetch an image from the provided URL and apply a blur filter. Returns the processed image directly.",
    "consumes": ["application/json"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image and blur parameters",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image"
                    },
                    "radius": {
                        "type": "number",
                        "description": "Blur radius (larger values create stronger blur)",
                        "default": 2.0
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Blurred image",
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
def blur_image_from_url():
    """
    Apply blur filter to image from URL and return the processed image.
    
    Data flow:
    1. Download image from URL
    2. Process image (apply blur)
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg",
        "radius": 2.0
    }
    """
    # Get URL from request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    image_url = data['url']
    
    # Get blur radius
    try:
        radius = float(data.get('radius', 2.0))
        if radius <= 0:
            return jsonify({'error': 'Blur radius must be positive'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid blur radius'}), 400
    
    # Validate URL
    if not is_valid_image_url(image_url):
        # Log invalid URL
        log_operation(
            image_name="unknown",
            operation=f"blur_{radius}",
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
            operation=f"blur_{radius}",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_blur",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Apply blur
    processed_path = apply_blur(file_path, radius, source_type="url")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/rotate', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Rotate an uploaded image",
    "description": "Upload an image and rotate it by the specified angle. Returns the processed image directly.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to process",
            "required": True,
            "type": "file"
        },
        {
            "name": "angle",
            "in": "formData",
            "description": "Rotation angle in degrees (clockwise)",
            "required": False,
            "type": "number",
            "default": 90
        }
    ],
    "responses": {
        "200": {
            "description": "Rotated image",
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
def rotate_image_endpoint():
    """
    Rotate an uploaded image and return the processed image.
    
    Data flow:
    1. Upload the image
    2. Process image (apply rotation)
    3. Return processed image directly
    """
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get rotation angle from form
    try:
        angle = float(request.form.get('angle', 90))
    except ValueError:
        return jsonify({'error': 'Invalid rotation angle'}), 400
    
    # Save the file if it's allowed
    filename, file_path = save_uploaded_file(file)
    
    if not file_path:
        # Log failed upload
        log_operation(
            image_name=file.filename if file.filename else "unknown",
            operation=f"rotate_{angle}",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_rotate",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Apply rotation
    processed_path = rotate_image(file_path, angle, source_type="upload")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/rotate-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Rotate an image from URL",
    "description": "Fetch an image from the provided URL and rotate it. Returns the processed image directly.",
    "consumes": ["application/json"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image and rotation parameters",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image"
                    },
                    "angle": {
                        "type": "number",
                        "description": "Rotation angle in degrees (clockwise)",
                        "default": 90
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Rotated image",
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
def rotate_image_from_url():
    """
    Rotate an image from URL and return the processed image.
    
    Data flow:
    1. Download image from URL
    2. Process image (apply rotation)
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg",
        "angle": 90
    }
    """
    # Get URL from request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    image_url = data['url']
    
    # Get rotation angle
    try:
        angle = float(data.get('angle', 90))
    except ValueError:
        return jsonify({'error': 'Invalid rotation angle'}), 400
    
    # Validate URL
    if not is_valid_image_url(image_url):
        # Log invalid URL
        log_operation(
            image_name="unknown",
            operation=f"rotate_{angle}",
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
            operation=f"rotate_{angle}",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_rotate",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Apply rotation
    processed_path = rotate_image(file_path, angle, source_type="url")
    
    if processed_path:
        # Return the processed image directly
        image_response = get_image_response(processed_path)
        if image_response:
            return image_response
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/resize', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Resize an uploaded image",
    "description": "Upload an image and resize it according to specified parameters. Returns the processed image directly.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to process",
            "required": True,
            "type": "file"
        },
        {
            "name": "width",
            "in": "formData",
            "description": "Target width in pixels",
            "required": False,
            "type": "integer"
        },
        {
            "name": "height",
            "in": "formData",
            "description": "Target height in pixels",
            "required": False,
            "type": "integer"
        },
        {
            "name": "type",
            "in": "formData",
            "description": "Resize type: 'free' or 'maintain_aspect_ratio'",
            "required": False,
            "type": "string",
            "enum": ["free", "maintain_aspect_ratio"],
            "default": "maintain_aspect_ratio"
        }
    ],
    "responses": {
        "200": {
            "description": "Resized image",
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
def resize_image_endpoint():
    """
    Resize an uploaded image and return the processed image.
    
    Data flow:
    1. Upload the image
    2. Process image (resize according to parameters)
    3. Return processed image directly
    """
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get resize parameters from form
    width = request.form.get('width', None)
    height = request.form.get('height', None)
    resize_type = request.form.get('type', 'maintain_aspect_ratio')
    
    # Validate and convert parameters
    try:
        width = int(width) if width else None
        height = int(height) if height else None
        
        if width is None and height is None:
            return jsonify({'error': 'At least one dimension (width or height) must be specified'}), 400
            
        if resize_type not in ["free", "maintain_aspect_ratio"]:
            return jsonify({'error': 'Resize type must be "free" or "maintain_aspect_ratio"'}), 400
    except ValueError:
        return jsonify({'error': 'Width and height must be integers'}), 400
    
    # Save the file if it's allowed
    filename, file_path = save_uploaded_file(file)
    
    if not file_path:
        # Log failed upload
        log_operation(
            image_name=file.filename if file.filename else "unknown",
            operation="resize",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_resize",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Apply resize
    try:
        processed_path = resize_image(
            file_path, 
            width=width, 
            height=height, 
            resize_type=resize_type, 
            source_type="upload"
        )
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/resize-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Resize an image from URL",
    "description": "Fetch an image from the provided URL and resize it. Returns the processed image directly.",
    "consumes": ["application/json"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image and resize parameters",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Target width in pixels"
                    },
                    "height": {
                        "type": "integer",
                        "description": "Target height in pixels"
                    },
                    "type": {
                        "type": "string",
                        "description": "Resize type: 'free' or 'maintain_aspect_ratio'",
                        "enum": ["free", "maintain_aspect_ratio"],
                        "default": "maintain_aspect_ratio"
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Resized image",
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
def resize_image_from_url():
    """
    Resize an image from URL and return the processed image.
    
    Data flow:
    1. Download image from URL
    2. Process image (resize according to parameters)
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg",
        "width": 800,
        "height": 600,
        "type": "maintain_aspect_ratio"
    }
    """
    # Get URL from request
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    image_url = data['url']
    
    # Get resize parameters
    width = data.get('width', None)
    height = data.get('height', None)
    resize_type = data.get('type', 'maintain_aspect_ratio')
    
    # Validate parameters
    if width is None and height is None:
        return jsonify({'error': 'At least one dimension (width or height) must be specified'}), 400
        
    if resize_type not in ["free", "maintain_aspect_ratio"]:
        return jsonify({'error': 'Resize type must be "free" or "maintain_aspect_ratio"'}), 400
        
    # Validate URL
    if not is_valid_image_url(image_url):
        # Log invalid URL
        log_operation(
            image_name="unknown",
            operation="resize",
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
            operation="resize",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_resize",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Apply resize
    try:
        processed_path = resize_image(
            file_path, 
            width=width, 
            height=height, 
            resize_type=resize_type, 
            source_type="url"
        )
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Error processing image'}), 500

@image_bp.route('/remove-background', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Remove background from an uploaded image",
    "description": "Upload an image and remove its background, keeping only the foreground subject. Returns the processed image with transparency.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/png"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to process",
            "required": True,
            "type": "file"
        }
    ],
    "responses": {
        "200": {
            "description": "Image with background removed",
            "content": {
                "image/png": {
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
def remove_background_endpoint():
    """
    Remove background from an uploaded image and return the processed image.
    
    Data flow:
    1. Upload the image
    2. Process image (remove background)
    3. Return processed image directly
    
    Note: This is a resource-intensive operation that may take longer than other processes.
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
            operation="bg_removal",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_bg_removal",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Process the image - this may take longer than other operations
    try:
        processed_path = remove_background(file_path, source_type="upload")
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
            
        return jsonify({'error': 'Error processing image'}), 500
    except Exception as e:
        current_app.logger.error(f"Error removing background: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@image_bp.route('/remove-background-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Remove background from an image at URL",
    "description": "Fetch an image from the provided URL and remove its background. Returns the processed image with transparency.",
    "consumes": ["application/json"],
    "produces": ["image/png"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image to process",
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
            "description": "Image with background removed",
            "content": {
                "image/png": {
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
def remove_background_from_url():
    """
    Remove background from an image at URL and return the processed image.
    
    Data flow:
    1. Download image from URL
    2. Process image (remove background)
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg"
    }
    
    Note: This is a resource-intensive operation that may take longer than other processes.
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
            operation="bg_removal",
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
            operation="bg_removal",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_bg_removal",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Process the image - this may take longer than other operations
    try:
        processed_path = remove_background(file_path, source_type="url")
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
            
        return jsonify({'error': 'Error processing image'}), 500
    except Exception as e:
        current_app.logger.error(f"Error removing background: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@image_bp.route('/transform', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Apply multiple transformations to an uploaded image",
    "description": "Upload an image and apply multiple transformations in a single request. Returns the processed image directly.",
    "consumes": ["multipart/form-data"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "image",
            "in": "formData",
            "description": "Image file to process",
            "required": True,
            "type": "file"
        },
        {
            "name": "transformations",
            "in": "formData",
            "description": "JSON string of transformations to apply",
            "required": True,
            "type": "string",
            "example": '{"grayscale": true, "blur": {"apply": true, "radius": 5}, "rotate": {"apply": true, "angle": 90}, "resize": {"apply": true, "width": 300, "height": 200, "type": "maintain_aspect_ratio"}, "remove_background": false}'
        }
    ],
    "responses": {
        "200": {
            "description": "Transformed image",
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
def transform_image_endpoint():
    """
    Apply multiple transformations to an uploaded image in a single request.
    
    The transformations are applied in this order:
    1. Background removal (if applied)
    2. Resize (if applied)
    3. Rotate (if applied)
    4. Grayscale (if applied)
    5. Blur (if applied)
    
    Data flow:
    1. Upload the image
    2. Process image with all requested transformations
    3. Return processed image directly
    """
    # Check if request has the file part
    if 'image' not in request.files:
        return jsonify({'error': 'No image part in the request'}), 400
    
    file = request.files['image']
    
    # Check if file is selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Get transformations from form
    try:
        transformations_json = request.form.get('transformations', '{}')
        transformations = json.loads(transformations_json)
        
        # Validate transformations
        if not isinstance(transformations, dict):
            return jsonify({'error': 'Transformations must be a valid JSON object'}), 400
            
        # Check if any transformations are requested
        if not any([
            transformations.get('grayscale'),
            transformations.get('blur', {}).get('apply'),
            transformations.get('rotate', {}).get('apply'),
            transformations.get('resize', {}).get('apply'),
            transformations.get('remove_background')
        ]):
            return jsonify({'error': 'No transformations specified'}), 400
            
    except json.JSONDecodeError:
        return jsonify({'error': 'Invalid JSON in transformations parameter'}), 400
    
    # Save the file if it's allowed
    filename, file_path = save_uploaded_file(file)
    
    if not file_path:
        # Log failed upload
        log_operation(
            image_name=file.filename if file.filename else "unknown",
            operation="transform",
            source_type="upload",
            status="error",
            details={"error": "File type not allowed"}
        )
        return jsonify({'error': 'File type not allowed'}), 400
    
    # Log the upload part of the operation
    log_operation(
        image_name=filename,
        operation="upload_for_transform",
        source_type="upload",
        details={"original_filename": file.filename, "saved_path": file_path}
    )
    
    # Apply transformations
    try:
        processed_path = apply_transformations(
            file_path, 
            transformations, 
            source_type="upload"
        )
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
        
        return jsonify({'error': 'Error processing image'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error applying transformations: {str(e)}")
        return jsonify({'error': str(e)}), 500

@image_bp.route('/transform-url', methods=['POST'])
@swag_from({
    "tags": ["Image Operations"],
    "summary": "Apply multiple transformations to an image at URL",
    "description": "Fetch an image from the provided URL and apply multiple transformations in a single request. Returns the processed image directly.",
    "consumes": ["application/json"],
    "produces": ["image/*"],
    "parameters": [
        {
            "name": "body",
            "in": "body",
            "description": "URL of the image and transformations to apply",
            "required": True,
            "schema": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the image"
                    },
                    "grayscale": {
                        "type": "boolean",
                        "description": "Apply grayscale conversion",
                        "default": False
                    },
                    "blur": {
                        "type": "object",
                        "description": "Blur transformation options",
                        "properties": {
                            "apply": {
                                "type": "boolean",
                                "default": False
                            },
                            "radius": {
                                "type": "number",
                                "default": 2
                            }
                        }
                    },
                    "rotate": {
                        "type": "object",
                        "description": "Rotate transformation options",
                        "properties": {
                            "apply": {
                                "type": "boolean",
                                "default": False
                            },
                            "angle": {
                                "type": "number",
                                "default": 90
                            }
                        }
                    },
                    "resize": {
                        "type": "object",
                        "description": "Resize transformation options",
                        "properties": {
                            "apply": {
                                "type": "boolean",
                                "default": False
                            },
                            "width": {
                                "type": "integer"
                            },
                            "height": {
                                "type": "integer"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["free", "maintain_aspect_ratio"],
                                "default": "maintain_aspect_ratio"
                            }
                        }
                    },
                    "remove_background": {
                        "type": "boolean",
                        "description": "Apply background removal",
                        "default": False
                    }
                }
            }
        }
    ],
    "responses": {
        "200": {
            "description": "Transformed image",
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
def transform_image_from_url():
    """
    Apply multiple transformations to an image from URL in a single request.
    
    The transformations are applied in this order:
    1. Background removal (if applied)
    2. Resize (if applied)
    3. Rotate (if applied)
    4. Grayscale (if applied)
    5. Blur (if applied)
    
    Data flow:
    1. Download image from URL
    2. Process image with all requested transformations
    3. Return processed image directly
    
    Expected JSON payload:
    {
        "url": "https://example.com/image.jpg",
        "grayscale": true,
        "blur": { "apply": true, "radius": 5 },
        "rotate": { "apply": true, "angle": 90 },
        "resize": { "apply": true, "width": 300, "height": 200, "type": "maintain_aspect_ratio" },
        "remove_background": false
    }
    """
    # Get request data
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'No URL provided'}), 400
    
    image_url = data['url']
    
    # Extract transformations
    transformations = {
        'grayscale': data.get('grayscale', False),
        'blur': data.get('blur', {}),
        'rotate': data.get('rotate', {}),
        'resize': data.get('resize', {}),
        'remove_background': data.get('remove_background', False)
    }
    
    # Check if any transformations are requested
    if not any([
        transformations.get('grayscale'),
        transformations.get('blur', {}).get('apply'),
        transformations.get('rotate', {}).get('apply'),
        transformations.get('resize', {}).get('apply'),
        transformations.get('remove_background')
    ]):
        return jsonify({'error': 'No transformations specified'}), 400
        
    # Validate URL
    if not is_valid_image_url(image_url):
        # Log invalid URL
        log_operation(
            image_name="unknown",
            operation="transform",
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
            operation="transform",
            source_type="url",
            status="error",
            details={"error": "Could not download image from URL", "url": image_url}
        )
        return jsonify({'error': 'Could not download image from URL'}), 400
    
    # Log the download part of the operation
    log_operation(
        image_name=filename,
        operation="download_for_transform",
        source_type="url",
        details={"url": image_url, "saved_path": file_path}
    )
    
    # Apply transformations
    try:
        processed_path = apply_transformations(
            file_path, 
            transformations, 
            source_type="url"
        )
        
        if processed_path:
            # Return the processed image directly
            image_response = get_image_response(processed_path)
            if image_response:
                return image_response
        
        return jsonify({'error': 'Error processing image'}), 500
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error applying transformations: {str(e)}")
        return jsonify({'error': str(e)}), 500