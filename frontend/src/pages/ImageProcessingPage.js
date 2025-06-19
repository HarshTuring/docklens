import React, { useState, useEffect, useRef } from 'react';
import { imageApi } from '../api/images';
import '../styles/components/imageProcessing.scss';

const ImageProcessingPage = () => {
    // State for form inputs
    const [imageSource, setImageSource] = useState('upload'); // 'upload' or 'url'
    const [imageUrl, setImageUrl] = useState('');
    const [selectedFile, setSelectedFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState('');
    const [uploadedMetadata, setUploadedMetadata] = useState(null);
    const [isUploading, setIsUploading] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [processedImageUrl, setProcessedImageUrl] = useState('');

    // Track image processing parameters
    const [transformations, setTransformations] = useState({
        grayscale: false,
        blur: {
            apply: false,
            radius: 2
        },
        rotate: {
            apply: false,
            angle: 90
        },
        resize: {
            apply: false,
            width: 800,
            height: 600,
            type: "maintain_aspect_ratio"
        },
        remove_background: false
    });

    // Refs
    const fileInputRef = useRef(null);

    // Clear file preview when unmounting
    useEffect(() => {
        return () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
            if (processedImageUrl) {
                URL.revokeObjectURL(processedImageUrl);
            }
        };
    }, []); // Empty dependency array - only run cleanup on unmount

    // Handle file selection
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        const validTypes = ['image/jpeg', 'image/png', 'image/gif'];
        if (!validTypes.includes(file.type)) {
            setError('Please select a valid image file (JPEG, PNG, or GIF)');
            return;
        }

        // Validate file size (max 10MB)
        if (file.size > 10 * 1024 * 1024) {
            setError('Image must be less than 10MB');
            return;
        }

        setSelectedFile(file);
        setError('');
        setProcessedImageUrl('');
        setUploadedMetadata(null);

        // Create preview URL
        const preview = URL.createObjectURL(file);
        setPreviewUrl(preview);
    };

    // Handle image source change
    const handleImageSourceChange = (source) => {
        setImageSource(source);
        setError('');
        setProcessedImageUrl('');
        setSuccessMessage('');

        // Clear existing data
        if (source === 'upload') {
            setImageUrl('');
        } else {
            setSelectedFile(null);
            setPreviewUrl('');
            setUploadedMetadata(null);
        }
    };

    // Handle image URL input
    const handleUrlChange = (e) => {
        setImageUrl(e.target.value);
        setError('');
        setProcessedImageUrl('');
        setSuccessMessage('');
    };

    // Handle upload button click
    const handleSelectFile = () => {
        fileInputRef.current.click();
    };

    // Toggle an operation on/off
    const toggleTransformation = (type) => {
        if (type === 'grayscale' || type === 'remove_background') {
            setTransformations({
                ...transformations,
                [type]: !transformations[type]
            });
        } else {
            setTransformations({
                ...transformations,
                [type]: {
                    ...transformations[type],
                    apply: !transformations[type].apply
                }
            });
        }
    };

    // Update operation parameters
    const updateTransformationParams = (type, paramName, value) => {
        setTransformations({
            ...transformations,
            [type]: {
                ...transformations[type],
                [paramName]: value
            }
        });
    };

    // Handle numeric input changes with validation
    const handleNumericInput = (e, type, paramName, min, max) => {
        let value = parseInt(e.target.value, 10);

        if (isNaN(value)) {
            value = min;
        } else {
            value = Math.max(min, Math.min(max, value));
        }

        updateTransformationParams(type, paramName, value);
    };

    // Upload image
    const uploadImage = async () => {
        if (!selectedFile) {
            setError('Please select an image to upload');
            return;
        }

        try {
            setIsUploading(true);
            setError('');
            setSuccessMessage('');

            const response = await imageApi.uploadImage(selectedFile);

            if (response && response.metadata_id) {
                setUploadedMetadata(response);
                setSuccessMessage('Image uploaded successfully!');
            } else {
                setError('Failed to upload image. Please try again.');
            }
        } catch (err) {
            console.error('Upload error:', err);
            setError(err.response?.data?.message || 'Failed to upload image. Please try again.');
        } finally {
            setIsUploading(false);
        }
    };

    // Process the image with selected operations
    const processImage = async () => {
        try {
            setIsProcessing(true);
            setError('');
            setSuccessMessage('');

            // Check if any transformation is selected
            const hasTransformations =
                transformations.grayscale ||
                transformations.blur.apply ||
                transformations.rotate.apply ||
                transformations.resize.apply ||
                transformations.remove_background;

            if (!hasTransformations) {
                setError('Please select at least one transformation to apply');
                setIsProcessing(false);
                return;
            }

            let response;

            if (imageSource === 'upload') {
                if (!selectedFile) {
                    setError('Please select an image to upload');
                    setIsProcessing(false);
                    return;
                }

                response = await imageApi.transformImage(selectedFile, transformations);
            } else if (imageSource === 'url') {
                if (!imageUrl.trim()) {
                    setError('Please enter a valid image URL');
                    setIsProcessing(false);
                    return;
                }

                response = await imageApi.transformImageUrl(imageUrl, transformations);
            }

            // Create URL from the blob response
            const imageObjectUrl = imageApi.createImageUrl(response);
            setProcessedImageUrl(imageObjectUrl);
            setSuccessMessage('Image processed successfully!');

        } catch (err) {
            console.error('Processing error:', err);
            setError(err.response?.data?.message || 'Failed to process image. Please try again.');
        } finally {
            setIsProcessing(false);
        }
    };

    return (
        <div className="image-processing-page">
            <div className="image-processing-container">
                <h1 className="image-processing-title">
                    Image Processing
                </h1>
                
                {error && (
                    <div className="image-processing-error">
                        {error}
                    </div>
                )}

                {successMessage && (
                    <div className="image-processing-success">
                        {successMessage}
                    </div>
                )}

                {/* Image Source Selection */}
                <div className="image-source-section">
                    <h2 className="section-title">
                        Image Source
                    </h2>
                    <div className="image-source-tabs">
                        <button 
                            className={`source-tab ${imageSource === 'upload' ? 'active' : ''}`}
                            onClick={() => handleImageSourceChange('upload')}
                        >
                            Upload Image
                        </button>
                        <button 
                            className={`source-tab ${imageSource === 'url' ? 'active' : ''}`}
                            onClick={() => handleImageSourceChange('url')}
                        >
                            Image URL
                        </button>
                    </div>
                    
                    {/* Upload Interface */}
                    {imageSource === 'upload' && (
                        <div className="upload-section">
                            <input
                                type="file"
                                accept="image/*"
                                onChange={handleFileChange}
                                ref={fileInputRef}
                                style={{ display: 'none' }}
                            />

                            <div
                                className="upload-area"
                                onClick={handleSelectFile}
                            >
                                {previewUrl ? (
                                    <img
                                        src={previewUrl}
                                        alt="Preview"
                                        className="image-preview"
                                    />
                                ) : (
                                    <div className="upload-placeholder">
                                        <span className="upload-icon">📁</span>
                                        <p className="upload-text">Click to select an image</p>
                                        <p className="upload-hint">JPEG, PNG or GIF, max 10MB</p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {/* URL Interface */}
                    {imageSource === 'url' && (
                        <div className="url-section">
                            <div className="url-input-group">
                                <input
                                    type="text"
                                    placeholder="Enter image URL"
                                    value={imageUrl}
                                    onChange={handleUrlChange}
                                    className="url-input"
                                />
                            </div>
                        </div>
                    )}
                </div>

                {/* Processing Options */}
                <div className="processing-options-section">
                    <h2 className="section-title">
                        Processing Options
                    </h2>
                    
                    {/* Grayscale */}
                    <div className="option-container">
                        <div className="option-header">
                            <label className="option-label">
                                <input
                                    type="checkbox"
                                    checked={transformations.grayscale}
                                    onChange={() => toggleTransformation('grayscale')}
                                    className="option-checkbox"
                                />
                                <span className="option-text">Grayscale</span>
                            </label>
                        </div>
                        <div className="option-description">
                            Convert image to black and white
                        </div>
                    </div>

                    {/* Blur */}
                    <div className="option-container">
                        <div className="option-header">
                            <label className="option-label">
                                <input
                                    type="checkbox"
                                    checked={transformations.blur.apply}
                                    onChange={() => toggleTransformation('blur')}
                                    className="option-checkbox"
                                />
                                <span className="option-text">Blur</span>
                            </label>
                        </div>
                        {transformations.blur.apply && (
                            <div className="option-params">
                                <div className="param-row">
                                    <label className="param-label">Radius:</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="50"
                                        value={transformations.blur.radius}
                                        onChange={(e) => handleNumericInput(e, 'blur', 'radius', 1, 50)}
                                        className="param-input"
                                    />
                                    <span className="param-hint">(1-50)</span>
                                </div>
                            </div>
                        )}
                        <div className="option-description">
                            Apply Gaussian blur to the image
                        </div>
                    </div>

                    {/* Rotate */}
                    <div className="option-container">
                        <div className="option-header">
                            <label className="option-label">
                                <input
                                    type="checkbox"
                                    checked={transformations.rotate.apply}
                                    onChange={() => toggleTransformation('rotate')}
                                    className="option-checkbox"
                                />
                                <span className="option-text">Rotate</span>
                            </label>
                        </div>
                        {transformations.rotate.apply && (
                            <div className="option-params">
                                <div className="param-row">
                                    <label className="param-label">Angle:</label>
                                    <select 
                                        onChange={(e) =>
                                            updateTransformationParams('rotate', 'angle', parseInt(e.target.value, 10))}
                                        className="param-select"
                                    >
                                        <option value="90">90°</option>
                                        <option value="180">180°</option>
                                        <option value="270">270°</option>
                                    </select>
                                </div>
                            </div>
                        )}
                        <div className="option-description">
                            Rotate the image by a specified angle
                        </div>
                    </div>

                    {/* Resize */}
                    <div className="option-container">
                        <div className="option-header">
                            <label className="option-label">
                                <input
                                    type="checkbox"
                                    checked={transformations.resize.apply}
                                    onChange={() => toggleTransformation('resize')}
                                    className="option-checkbox"
                                />
                                <span className="option-text">Resize</span>
                            </label>
                        </div>
                        {transformations.resize.apply && (
                            <div className="option-params">
                                <div className="param-row">
                                    <label className="param-label">Width:</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="5000"
                                        value={transformations.resize.width}
                                        onChange={(e) => handleNumericInput(e, 'resize', 'width', 1, 5000)}
                                        className="param-input"
                                    />
                                    <span className="param-hint">px</span>
                                </div>
                                <div>
                                    <label className="param-label">Height:</label>
                                    <input
                                        type="number"
                                        min="1"
                                        max="5000"
                                        value={transformations.resize.height}
                                        onChange={(e) => handleNumericInput(e, 'resize', 'height', 1, 5000)}
                                        className="param-input"
                                    />
                                    <span className="param-hint">px</span>
                                </div>
                                <div>
                                    <label className="param-label">
                                        <input
                                            type="checkbox"
                                            checked={transformations.resize.type === "maintain_aspect_ratio"}
                                            onChange={(e) => updateTransformationParams('resize', 'type',
                                                e.target.checked ? "maintain_aspect_ratio" : "free")}
                                            className="param-checkbox"
                                        />
                                        <span className="param-text">Preserve aspect ratio</span>
                                    </label>
                                </div>
                            </div>
                        )}
                        <div className="option-description">
                            Change image dimensions
                        </div>
                    </div>

                    {/* Background Removal */}
                    <div className="option-container">
                        <div className="option-header">
                            <label className="option-label">
                                <input
                                    type="checkbox"
                                    checked={transformations.remove_background}
                                    onChange={() => toggleTransformation('remove_background')}
                                    className="option-checkbox"
                                />
                                <span className="option-text">Background Removal</span>
                            </label>
                        </div>
                        <div className="option-description">
                            Remove the background from the image
                        </div>
                        {transformations.remove_background && (
                            <div className="option-hint">
                                This operation may take longer to process
                            </div>
                        )}
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="action-buttons">
                    <button onClick={processImage}>
                        {isProcessing ? 'Processing...' : 'Process Image'}
                    </button>
                </div>
                {/* Results Section */}
                {processedImageUrl && (
                    <div className="results-section">
                        <h2 className="section-title">
                            Processed Image
                        </h2>
                        <div className="result-image-container">
                            <img
                                src={processedImageUrl}
                                alt="Processed"
                                className="result-image"
                            />
                        </div>
                        <div>
                            <a>
                                Download Image
                            </a>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ImageProcessingPage;