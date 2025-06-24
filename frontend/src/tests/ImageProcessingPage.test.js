import React from 'react';
import { render, screen } from '@testing-library/react';
import ImageProcessingPage from '../pages/ImageProcessingPage';

// Mock imageApi
jest.mock('../api/images', () => ({
  imageApi: {
    uploadImage: jest.fn(),
    transformImage: jest.fn(),
    transformImageUrl: jest.fn(),
    createImageUrl: jest.fn()
  }
}));

describe('ImageProcessingPage', () => {
  test('renders title, image source tabs, and process image button', () => {
    render(<ImageProcessingPage />);
    expect(screen.getByText(/image processing/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /upload image/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /image url/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /process image/i })).toBeInTheDocument();
  });
}); 