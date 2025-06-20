import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';

const ProtectedRoute = () => {
    const { isAuthenticated, loading } = useAuth();

    // Show loading state while checking authentication
    if (loading) {
        return
        <div>
            Loading...

        </div>
            ;
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return

        <Navigate to="/login" replace />
            ;
    }

    // Render child routes if authenticated
    return

    <Outlet />
        ;
};

export default ProtectedRoute;

