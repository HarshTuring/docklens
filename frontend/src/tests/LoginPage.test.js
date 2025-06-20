import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router';
import LoginPage from '../pages/LoginPage';

// Mock AuthContext
jest.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ login: jest.fn(), error: null })
}));

describe('LoginPage', () => {
  test('renders email, password fields and sign in button', () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });
}); 