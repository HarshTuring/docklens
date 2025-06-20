import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '../contexts/AuthContext';
import '../styles/global.scss';
import '../styles/components/auth.scss';

const LoginPage = () => {
    const [formData, setFormData] = useState({
        email: '',
        password: '',
    });
    const [submitting, setSubmitting] = useState(false);
    const { login, error } = useAuth();
    const navigate = useNavigate();

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSubmitting(true);

        try {
            const { email, password } = formData;
            const success = await login(email, password);

            if (success) {
                navigate('/dashboard');
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-page">
            <div className="login-card">
                <h1 className="login-title">
                    Sign In
                </h1>
                <p className="login-subtitle">
                    Access your Image Processing dashboard
                </p>
                {error && <div className="login-error-message">{error}</div>}

                <form className="login-form">
                    <div className="login-form-group">
                        <label className="login-label" htmlFor="email">
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            autoComplete="email"
                            className="login-input"
                        />
                    </div>
                    <div className="login-form-group">
                        <label className="login-label" htmlFor="password">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            autoComplete="current-password"
                            className="login-input"
                        />
                    </div>
                    <button className="login-submit-btn" onClick={handleSubmit}>
                        {submitting ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>
                <div className="login-links-wrapper">
                    <p className="login-signup-link-text">
                        Don't have an account?
                        <Link className="login-signup-link" to="/register">
                            Sign up
                        </Link>
                    </p>
                    <Link className="login-forgot-link" to="/forgot-password">
                        Forgot password?
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default LoginPage;