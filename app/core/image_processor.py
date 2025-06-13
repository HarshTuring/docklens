from PIL import Image
import os
import uuid
from flask import current_app
from app.utils.logger import log_operation
from app.services.mongodb_service import ImageMetadataService
from app.services.redis_service import ImageCacheService

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
        # First check if we have a cached version
        cached_path = ImageCacheService.find_processed_image(file_path, "grayscale")
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for grayscale processing: {file_path}")
            
            # Update MongoDB with processing info (reusing cached version)
            ImageMetadataService.save_processed_image(
                original_filename=os.path.basename(file_path),
                original_path=file_path,
                processed_path=cached_path,
                operation="grayscale",
                source_type=source_type
            )
            
            return cached_path

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

        ImageCacheService.cache_processed_image(file_path, output_path, "grayscale")

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
    
def apply_blur(file_path, radius=2.0, source_type="upload"):
    """
    Apply a Gaussian blur filter to an image.
    
    Args:
        file_path: Path to the image to be blurred
        radius: Blur radius (higher values produce more blur)
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the processed image
    """
    try:
        # First check if we have a cached version
        cached_path = ImageCacheService.find_processed_image(
            file_path, 
            f"blur_{radius}"
        )
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for blur processing: {file_path}")
            
            # Update MongoDB with processing info (reusing cached version)
            ImageMetadataService.save_processed_image(
                original_filename=os.path.basename(file_path),
                original_path=file_path,
                processed_path=cached_path,
                operation=f"blur_{radius}",
                source_type=source_type
            )
            
            return cached_path

        # Open the image
        img = Image.open(file_path)
        
        # Apply Gaussian blur
        from PIL import ImageFilter
        blurred_img = img.filter(ImageFilter.GaussianBlur(radius=float(radius)))
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(current_app.static_folder, 'processed_images')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique filename for processed image
        filename = os.path.basename(file_path)
        output_filename = f"blur_{radius}_{uuid.uuid4().hex}_{filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the blurred image
        blurred_img.save(output_path)
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation=f"blur_{radius}",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "radius": radius
            }
        )

        # Cache the processed image
        ImageCacheService.cache_processed_image(
            file_path, 
            output_path, 
            f"blur_{radius}"
        )

        # Save processing metadata to MongoDB
        ImageMetadataService.save_processed_image(
            original_filename=filename,
            original_path=file_path,
            processed_path=output_path,
            operation=f"blur_{radius}",
            source_type=source_type
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error applying blur to image: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation=f"blur_{radius}",
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        return None

def rotate_image(file_path, angle=0, source_type="upload"):
    """
    Rotate an image by the specified angle.
    
    Args:
        file_path: Path to the image to be rotated
        angle: Rotation angle in degrees (clockwise)
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the processed image
    """
    try:
        # First check if we have a cached version
        cached_path = ImageCacheService.find_processed_image(
            file_path, 
            f"rotate_{angle}"
        )
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for rotate processing: {file_path}")
            
            # Update MongoDB with processing info (reusing cached version)
            ImageMetadataService.save_processed_image(
                original_filename=os.path.basename(file_path),
                original_path=file_path,
                processed_path=cached_path,
                operation=f"rotate_{angle}",
                source_type=source_type
            )
            
            return cached_path

        # Open the image
        img = Image.open(file_path)
        
        # Apply rotation (expand=True to prevent cropping)
        rotated_img = img.rotate(angle * -1, expand=True)  # PIL rotates counter-clockwise
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(current_app.static_folder, 'processed_images')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique filename for processed image
        filename = os.path.basename(file_path)
        output_filename = f"rotate_{angle}_{uuid.uuid4().hex}_{filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the rotated image
        rotated_img.save(output_path)
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation=f"rotate_{angle}",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "angle": angle
            }
        )

        # Cache the processed image
        ImageCacheService.cache_processed_image(
            file_path, 
            output_path, 
            f"rotate_{angle}"
        )

        # Save processing metadata to MongoDB
        ImageMetadataService.save_processed_image(
            original_filename=filename,
            original_path=file_path,
            processed_path=output_path,
            operation=f"rotate_{angle}",
            source_type=source_type
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error rotating image: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation=f"rotate_{angle}",
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        return None

def resize_image(file_path, width=None, height=None, resize_type="maintain_aspect_ratio", source_type="upload"):
    """
    Resize an image based on the specified parameters.
    
    Args:
        file_path: Path to the image to be resized
        width: Target width in pixels
        height: Target height in pixels
        resize_type: Resize type - "free" or "maintain_aspect_ratio"
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the processed image
    """
    try:
        # Validate parameters
        if width is None and height is None:
            raise ValueError("At least one dimension (width or height) must be specified")
        
        if width is not None and width <= 0:
            raise ValueError("Width must be a positive number")
            
        if height is not None and height <= 0:
            raise ValueError("Height must be a positive number")
        
        if resize_type not in ["free", "maintain_aspect_ratio"]:
            raise ValueError("Resize type must be 'free' or 'maintain_aspect_ratio'")
        
        # Create a cache key based on resize parameters
        operation_key = f"resize_{resize_type}"
        if width is not None:
            operation_key += f"_w{width}"
        if height is not None:
            operation_key += f"_h{height}"
        
        # First check if we have a cached version
        cached_path = ImageCacheService.find_processed_image(
            file_path, 
            operation_key
        )
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for resize processing: {file_path}")
            
            # Update MongoDB with processing info (reusing cached version)
            ImageMetadataService.save_processed_image(
                original_filename=os.path.basename(file_path),
                original_path=file_path,
                processed_path=cached_path,
                operation=operation_key,
                source_type=source_type
            )
            
            return cached_path

        # Open the image
        img = Image.open(file_path)
        original_width, original_height = img.size
        
        # Calculate new dimensions based on resize type
        if resize_type == "free":
            # Use specified dimensions as-is
            new_width = width if width is not None else original_width
            new_height = height if height is not None else original_height
        else:  # maintain_aspect_ratio
            aspect_ratio = original_width / original_height
            
            if width is not None and height is not None:
                # Prioritize width, adjust height to maintain aspect ratio
                new_width = width
                new_height = int(width / aspect_ratio)
            elif width is not None:
                # Only width specified, calculate height
                new_width = width
                new_height = int(width / aspect_ratio)
            elif height is not None:
                # Only height specified, calculate width
                new_height = height
                new_width = int(height * aspect_ratio)
        
        # Resize the image
        resized_img = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(current_app.static_folder, 'processed_images')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique filename for processed image
        filename = os.path.basename(file_path)
        output_filename = f"resize_{resize_type}_{new_width}x{new_height}_{uuid.uuid4().hex}_{filename}"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the resized image
        resized_img.save(output_path)
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation=operation_key,
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "original_dimensions": f"{original_width}x{original_height}",
                "new_dimensions": f"{new_width}x{new_height}",
                "resize_type": resize_type
            }
        )

        # Cache the processed image
        ImageCacheService.cache_processed_image(
            file_path, 
            output_path, 
            operation_key
        )

        # Save processing metadata to MongoDB
        ImageMetadataService.save_processed_image(
            original_filename=filename,
            original_path=file_path,
            processed_path=output_path,
            operation=operation_key,
            source_type=source_type
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error resizing image: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation="resize",
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        # Re-raise with a user-friendly message
        if isinstance(e, ValueError):
            raise ValueError(str(e))
        else:
            raise Exception(f"Error processing image: {str(e)}")
        
def remove_background(file_path, source_type="upload"):
    """
    Remove the background from an image, keeping only the foreground subject.
    
    Args:
        file_path: Path to the image to process
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the processed image
    """
    try:
        # First check if we have a cached version
        cached_path = ImageCacheService.find_processed_image(
            file_path, 
            "bg_removal"
        )
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for background removal: {file_path}")
            
            # Update MongoDB with processing info (reusing cached version)
            ImageMetadataService.save_processed_image(
                original_filename=os.path.basename(file_path),
                original_path=file_path,
                processed_path=cached_path,
                operation="bg_removal",
                source_type=source_type
            )
            
            return cached_path

        # Import rembg here to avoid loading the model unless necessary
        from rembg import remove
        
        # Open the image
        img = Image.open(file_path)
        
        # Log the start of processing - this can take time
        current_app.logger.info(f"Starting background removal for {file_path}")
        
        # Remove background
        output_img = remove(img)
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(current_app.static_folder, 'processed_images')
        os.makedirs(output_dir, exist_ok=True)
        
        # Create unique filename for processed image - always use PNG for transparency
        filename = os.path.basename(file_path)
        name, _ = os.path.splitext(filename)  # Ignore original extension
        output_filename = f"nobg_{name}_{uuid.uuid4().hex}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the processed image as PNG to preserve transparency
        output_img.save(output_path, 'PNG')
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation="bg_removal",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename
            }
        )

        # Cache the processed image
        ImageCacheService.cache_processed_image(
            file_path, 
            output_path, 
            "bg_removal"
        )

        # Save processing metadata to MongoDB
        ImageMetadataService.save_processed_image(
            original_filename=filename,
            original_path=file_path,
            processed_path=output_path,
            operation="bg_removal",
            source_type=source_type
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error removing background: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation="bg_removal",
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        raise Exception(f"Error removing background: {str(e)}")