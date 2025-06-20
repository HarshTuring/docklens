import apiClient from './apiClient';

const AUTH_URL = 'http://localhost:5002';

export const authApi = {
  login: async (email, password) => {
    const response = await apiClient.post(`${AUTH_URL}/auth/login`, {
      email,
      password,
    });
    return response.data;
  },

  register: async (userData) => {
    const response = await apiClient.post(`${AUTH_URL}/auth/register`, userData);
    return response.data;
  },

  refreshToken: async (refreshToken) => {
    const response = await apiClient.post(`${AUTH_URL}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  logout: async () => {
    return await apiClient.post(`${AUTH_URL}/auth/logout`);
  },

  getCurrentUser: async () => {
    const response = await apiClient.get(`${AUTH_URL}/auth/me`);
    return response.data;
  }
};