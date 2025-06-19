import apiClient from './apiClient';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001';
const API_BASE = `${API_URL}/api`;

export const imageApi = {
    // Upload an image from file
    uploadImage: async (file) => {
        const formData = new FormData();
        formData.append('image', file);

        const response = await apiClient.post(`${API_BASE}/images/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
        return response.data;
    },

    // Transform image by URL with multiple operations
    transformImageUrl: async (url, transformations) => {
        // Directly use the transform-url endpoint with the correct request format
        const response = await apiClient.post(`${API_BASE}/images/transform-url`, {
            url,
            ...transformations // Spread the transformation options
        }, {
            responseType: 'blob' // Important: we're receiving binary image data
        });
        return response;
    },

    // Transform uploaded image with multiple operations
    transformImage: async (file, transformations) => {
        const formData = new FormData();
        formData.append('image', file);

        // Convert transformations object to JSON string
        formData.append('transformations', JSON.stringify(transformations));

        const response = await apiClient.post(`${API_BASE}/images/transform`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            responseType: 'blob' // Important: we're receiving binary image data
        });
        return response;
    },

    // Helper function to create object URL from blob response
    createImageUrl: (response) => {
        return URL.createObjectURL(response.data);
    }
};