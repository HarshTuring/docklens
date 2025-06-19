import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ImageProcessingPage from './pages/ImageProcessingPage';
// import DashboardPage from './pages/DashboardPage';
// import ImageEditorPage from './pages/ImageEditorPage';
// import GalleryPage from './pages/GalleryPage';
// import ProfilePage from './pages/ProfilePage';
// import NotFoundPage from './pages/NotFoundPage';

// Components
import ProtectedRoute from './components/auth/ProtectedRoute';
// import Header from './components/common/Header';

// Styles
// import './styles/global.scss';

const App = () => {
    return (
        <AuthProvider>
            <Router>
                <div>
                    <Routes>
                        {/* Public routes */}
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/dashboard" element={<ImageProcessingPage />} />

                        {/* Protected routes */}
                        <Route element={<ProtectedRoute />}></Route>
                        {/* 404 route can be added here if needed */}
                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
};

export default App;