from PIL import Image
import os
import uuid
from flask import current_app
from app.utils.logger import log_operation
from app.services.mongodb_service import ImageMetadataService

def process_image(file_path):
    """
    Process the uploaded image (placeholder for future processing).
    
    Args:
        file_path: Path to the uploaded image
        
    Returns:
        dict: Processing results
    """
    # Log the operation
    image_name = os.path.basename(file_path)
    log_operation(
        image_name=image_name,
        operation="register",
        source_type="upload",
        details={"file_path": file_path}
    )
    
    # This is just a placeholder for future image processing
    return {
        'status': 'processed',
        'message': 'Image successfully registered for processing',
        'file': file_path
    }

def convert_to_grayscale(file_path, source_type="upload"):
    """
    Convert an image to grayscale.
    
    Args:
        file_path: Path to the image to be converted
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the processed image
    """
    try:
        # Open the image
        img = Image.open(file_path)
        
        # Convert to grayscale
        gray_img = img.convert('L')
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(current_app.static_folder, 'processed_images')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique filename for processed image
        filename = os.path.basename(file_path)
        output_filename = f"gray_{uuid.uuid4().hex}_{filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the grayscale image
        gray_img.save(output_path)
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation="grayscale",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename
            }
        )

        ImageMetadataService.save_processed_image(
            original_filename=filename,
            original_path=file_path,
            processed_path=output_path,
            operation="grayscale",
            source_type=source_type
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error processing image: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation="grayscale",
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        return None