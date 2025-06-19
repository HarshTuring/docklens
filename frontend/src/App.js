import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';

// Pages
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
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


                        <Route path="/register" element={<RegisterPage />

                        } />
                        <Route path="/login" element={<LoginPage />
                        } />

                        {/* Protected routes */}
                        {/* <Route element={<ProtectedRoute />

                        }>

                            <Route path="/" element={<Navigate to="/dashboard" replace />

                            } />
                            <Route path="/dashboard" element={
                                <>

                                    <Header />
                                    <DashboardPage />
                                </>
                            } />
                            <Route path="/editor" element={
                                <>
                                    <Header />
                                    <ImageEditorPage />
                                </>
                            } />
                            <Route path="/gallery" element={
                                <>
                                    <Header />
                                    <GalleryPage />
                                </>
                            } />
                            <Route path="/profile" element={
                                <>
                                    <Header />
                                    <ProfilePage />
                                </>
                            } />
                        </Route> */}
                        {/* 404 route */}
                        {/* <Route path="*" element={<NotFoundPage /> */}

                        {/* } /> */}

                    </Routes>
                </div>
            </Router>
        </AuthProvider>
    );
};

export default App;