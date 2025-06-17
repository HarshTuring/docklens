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
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params={"grayscale": True}
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params={"grayscale": True}
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
        
        # Get or create original image record
        original_image = ImageMetadataService.get_original_image_by_path(file_path)
        if not original_image:
            original_image_id = ImageMetadataService.save_original_image(
                filename=filename,
                file_path=file_path,
                original_filename=filename,
                source_type=source_type
            )
        else:
            original_image_id = original_image['_id']
        
        # Create version record
        version_number = ImageMetadataService.get_next_version_number(original_image_id)
        ImageMetadataService.create_image_version(
            original_image_id=original_image_id,
            processed_path=output_path,
            operation_params={"grayscale": True}
        )
        
        # Cache the version
        ImageCacheService.cache_image_version(
            original_image_id=original_image_id,
            version_number=version_number,
            processed_path=output_path,
            operation_params={"grayscale": True}
        )
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation="grayscale",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "original_image_id": str(original_image_id),
                "version_number": version_number
            }
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
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params={"blur": {"apply": True, "radius": radius}}
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params={"blur": {"apply": True, "radius": radius}}
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
        
        # Get or create original image record
        original_image = ImageMetadataService.get_original_image_by_path(file_path)
        if not original_image:
            original_image_id = ImageMetadataService.save_original_image(
                filename=filename,
                file_path=file_path,
                original_filename=filename,
                source_type=source_type
            )
        else:
            original_image_id = original_image['_id']
        
        # Create version record
        version_number = ImageMetadataService.get_next_version_number(original_image_id)
        ImageMetadataService.create_image_version(
            original_image_id=original_image_id,
            processed_path=output_path,
            operation_params={"blur": {"apply": True, "radius": radius}}
        )
        
        # Cache the version
        ImageCacheService.cache_image_version(
            original_image_id=original_image_id,
            version_number=version_number,
            processed_path=output_path,
            operation_params={"blur": {"apply": True, "radius": radius}}
        )
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation=f"blur_{radius}",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "radius": radius,
                "original_image_id": str(original_image_id),
                "version_number": version_number
            }
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
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params={"rotate": {"apply": True, "angle": angle}}
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params={"rotate": {"apply": True, "angle": angle}}
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
        
        # Get or create original image record
        original_image = ImageMetadataService.get_original_image_by_path(file_path)
        if not original_image:
            original_image_id = ImageMetadataService.save_original_image(
                filename=filename,
                file_path=file_path,
                original_filename=filename,
                source_type=source_type
            )
        else:
            original_image_id = original_image['_id']
        
        # Create version record
        version_number = ImageMetadataService.get_next_version_number(original_image_id)
        ImageMetadataService.create_image_version(
            original_image_id=original_image_id,
            processed_path=output_path,
            operation_params={"rotate": {"apply": True, "angle": angle}}
        )
        
        # Cache the version
        ImageCacheService.cache_image_version(
            original_image_id=original_image_id,
            version_number=version_number,
            processed_path=output_path,
            operation_params={"rotate": {"apply": True, "angle": angle}}
        )
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation=f"rotate_{angle}",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "angle": angle,
                "original_image_id": str(original_image_id),
                "version_number": version_number
            }
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
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params={
                    "resize": {
                        "apply": True,
                        "width": width,
                        "height": height,
                        "type": resize_type
                    }
                }
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params={
                    "resize": {
                        "apply": True,
                        "width": width,
                        "height": height,
                        "type": resize_type
                    }
                }
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
        
        # Get or create original image record
        original_image = ImageMetadataService.get_original_image_by_path(file_path)
        if not original_image:
            original_image_id = ImageMetadataService.save_original_image(
                filename=filename,
                file_path=file_path,
                original_filename=filename,
                source_type=source_type
            )
        else:
            original_image_id = original_image['_id']
        
        # Create version record
        version_number = ImageMetadataService.get_next_version_number(original_image_id)
        ImageMetadataService.create_image_version(
            original_image_id=original_image_id,
            processed_path=output_path,
            operation_params={
                "resize": {
                    "apply": True,
                    "width": width,
                    "height": height,
                    "type": resize_type
                }
            }
        )
        
        # Cache the version
        ImageCacheService.cache_image_version(
            original_image_id=original_image_id,
            version_number=version_number,
            processed_path=output_path,
            operation_params={
                "resize": {
                    "apply": True,
                    "width": width,
                    "height": height,
                    "type": resize_type
                }
            }
        )
        
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
                "resize_type": resize_type,
                "original_image_id": str(original_image_id),
                "version_number": version_number
            }
        )
        
        return output_path
    except Exception as e:
        current_app.logger.error(f"Error resizing image: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation=operation_key,
            source_type=source_type,
            status="error",
            details={"error": str(e)}
        )
        
        return None

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
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params={"remove_background": True}
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params={"remove_background": True}
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
        name, _ = os.path.splitext(filename)
        output_filename = f"nobg_{name}_{uuid.uuid4().hex}.png"
        output_path = os.path.join(output_dir, output_filename)
        
        # Save the processed image as PNG to preserve transparency
        output_img.save(output_path, 'PNG')
        
        # Get or create original image record
        original_image = ImageMetadataService.get_original_image_by_path(file_path)
        if not original_image:
            original_image_id = ImageMetadataService.save_original_image(
                filename=filename,
                file_path=file_path,
                original_filename=filename,
                source_type=source_type
            )
        else:
            original_image_id = original_image['_id']
        
        # Create version record
        version_number = ImageMetadataService.get_next_version_number(original_image_id)
        ImageMetadataService.create_image_version(
            original_image_id=original_image_id,
            processed_path=output_path,
            operation_params={"remove_background": True}
        )
        
        # Cache the version
        ImageCacheService.cache_image_version(
            original_image_id=original_image_id,
            version_number=version_number,
            processed_path=output_path,
            operation_params={"remove_background": True}
        )
        
        # Log the operation
        log_operation(
            image_name=filename,
            operation="bg_removal",
            source_type=source_type,
            details={
                "input_path": file_path,
                "output_path": output_path,
                "output_filename": output_filename,
                "original_image_id": str(original_image_id),
                "version_number": version_number
            }
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
    
def apply_transformations(file_path, transformations, source_type="upload"):
    """
    Apply multiple transformations to an image in sequence.
    
    Args:
        file_path: Path to the image to process
        transformations: Dictionary of transformations to apply
        source_type: Source of the image (upload, url)
        
    Returns:
        str: Path to the final processed image
    """
    try:
        # Keep track of the current working image path
        current_path = file_path
        operations_applied = []
        
        # Generate a unique operation key based on all transformations
        operation_key = "transform_"
        if transformations.get('remove_background'):
            operation_key += "bg_"
        if transformations.get('grayscale'):
            operation_key += "gray_"
        if transformations.get('blur', {}).get('apply'):
            radius = transformations['blur'].get('radius', 2)
            operation_key += f"blur{radius}_"
        if transformations.get('rotate', {}).get('apply'):
            angle = transformations['rotate'].get('angle', 90)
            operation_key += f"rot{angle}_"
        if transformations.get('resize', {}).get('apply'):
            width = transformations['resize'].get('width')
            height = transformations['resize'].get('height')
            resize_type = transformations['resize'].get('type', 'maintain_aspect_ratio')
            operation_key += f"resize{width}x{height}_{resize_type}_"
            
        # Add a unique identifier to ensure uniqueness
        operation_key += uuid.uuid4().hex[:8]
        
        # First check if we have a cached version of the complete transformation
        cached_path = ImageCacheService.find_processed_image(
            file_path, 
            operation_key
        )
        
        # If we found a cached version and the file exists
        if cached_path and os.path.exists(cached_path):
            # Log cache hit
            current_app.logger.info(f"Cache hit for combined transformations: {file_path}")
            
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=cached_path,
                operation_params=transformations
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=cached_path,
                operation_params=transformations
            )
            
            return cached_path
        
        # Apply transformations in a specific order for best results
        
        # 1. Background Removal (should be first if applied)
        if transformations.get('remove_background'):
            current_app.logger.info(f"Applying background removal to {current_path}")
            processed_path = remove_background(current_path, source_type=source_type)
            if processed_path:
                operations_applied.append("background_removal")
                current_path = processed_path
                
        # 2. Resize (should be done early for efficiency)
        resize_config = transformations.get('resize', {})
        if resize_config.get('apply'):
            width = resize_config.get('width')
            height = resize_config.get('height')
            resize_type = resize_config.get('type', 'maintain_aspect_ratio')
            
            current_app.logger.info(f"Applying resize to {current_path}")
            processed_path = resize_image(
                current_path, 
                width=width, 
                height=height, 
                resize_type=resize_type, 
                source_type=source_type
            )
            if processed_path:
                operations_applied.append("resize")
                current_path = processed_path
                
        # 3. Rotation
        rotate_config = transformations.get('rotate', {})
        if rotate_config.get('apply'):
            angle = rotate_config.get('angle', 90)
            
            current_app.logger.info(f"Applying rotation to {current_path}")
            processed_path = rotate_image(current_path, angle, source_type=source_type)
            if processed_path:
                operations_applied.append("rotate")
                current_path = processed_path
                
        # 4. Grayscale
        if transformations.get('grayscale'):
            current_app.logger.info(f"Applying grayscale to {current_path}")
            processed_path = convert_to_grayscale(current_path, source_type=source_type)
            if processed_path:
                operations_applied.append("grayscale")
                current_path = processed_path
                
        # 5. Blur (should generally be last)
        blur_config = transformations.get('blur', {})
        if blur_config.get('apply'):
            radius = blur_config.get('radius', 2)
            
            current_app.logger.info(f"Applying blur to {current_path}")
            processed_path = apply_blur(current_path, radius, source_type=source_type)
            if processed_path:
                operations_applied.append("blur")
                current_path = processed_path
        
        # Cache the final result with the combined operation key
        if operations_applied and current_path != file_path:
            # Get or create original image record
            original_image = ImageMetadataService.get_original_image_by_path(file_path)
            if not original_image:
                original_image_id = ImageMetadataService.save_original_image(
                    filename=os.path.basename(file_path),
                    file_path=file_path,
                    original_filename=os.path.basename(file_path),
                    source_type=source_type
                )
            else:
                original_image_id = original_image['_id']
            
            # Create version record
            version_number = ImageMetadataService.get_next_version_number(original_image_id)
            ImageMetadataService.create_image_version(
                original_image_id=original_image_id,
                processed_path=current_path,
                operation_params=transformations
            )
            
            # Cache the version
            ImageCacheService.cache_image_version(
                original_image_id=original_image_id,
                version_number=version_number,
                processed_path=current_path,
                operation_params=transformations
            )
            
            # Log the combined operation
            log_operation(
                image_name=os.path.basename(file_path),
                operation="combined_transformations",
                source_type=source_type,
                details={
                    "input_path": file_path,
                    "output_path": current_path,
                    "operations_applied": operations_applied,
                    "transformations": transformations,
                    "original_image_id": str(original_image_id),
                    "version_number": version_number
                }
            )
            
        return current_path
        
    except Exception as e:
        current_app.logger.error(f"Error applying transformations: {str(e)}")
        
        # Log the error
        image_name = os.path.basename(file_path)
        log_operation(
            image_name=image_name,
            operation="combined_transformations",
            source_type=source_type,
            status="error",
            details={
                "error": str(e),
                "transformations": transformations
            }
        )
        
        raise Exception(f"Error applying transformations: {str(e)}")