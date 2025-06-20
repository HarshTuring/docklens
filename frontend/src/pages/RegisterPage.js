import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router';
import { useAuth } from '../contexts/AuthContext';

const RegisterPage = () => {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        password: '',
        confirmPassword: '',
    });
    const [errors, setErrors] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const { register, error } = useAuth();
    const navigate = useNavigate();

    const validateForm = () => {
        const newErrors = {};

        if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'Passwords do not match';
        }

        if (formData.password.length < 8) {
            newErrors.password = 'Password must be at least 8 characters';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData({ ...formData, [name]: value });

        // Clear error when field is edited
        if (errors[name]) {
            setErrors({ ...errors, [name]: null });
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!validateForm()) return;

        setSubmitting(true);

        try {
            const userData = {
                first_name: formData.first_name,
                last_name: formData.last_name,
                email: formData.email,
                password: formData.password,
            };

            const success = await register(userData);

            if (success) {
                navigate('/login', {
                    state: { message: 'Registration successful! Please log in.' }
                });
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="register-page">
            <div className="register-card">
                <h1 className="register-title">
                    Create Account
                </h1>
                <p className="register-subtitle">
                    Join our Image Processing platform
                </p>
                {error && <div className="register-error-message">{error}</div>}

                <form className="register-form">
                    <div className="register-form-group">
                        <label className="register-label" htmlFor="first_name">
                            First Name
                        </label>
                        <input
                            id="first_name"
                            type="text"
                            name="first_name"
                            value={formData.first_name}
                            onChange={handleChange}
                            required
                            className="register-input"
                        />
                    </div>
                    <div className="register-form-group">
                        <label className="register-label" htmlFor="last_name">
                            Last Name
                        </label>
                        <input
                            id="last_name"
                            type="text"
                            name="last_name"
                            value={formData.last_name}
                            onChange={handleChange}
                            required
                            className="register-input"
                        />
                    </div>
                    <div className="register-form-group">
                        <label className="register-label" htmlFor="email">
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleChange}
                            required
                            className="register-input"
                        />
                        {errors.email &&
                            <span className="register-error-text">
                                {errors.email}
                            </span>
                        }
                    </div>
                    <div className="register-form-group">
                        <label className="register-label" htmlFor="password">
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleChange}
                            required
                            className="register-input"
                        />
                        {errors.password &&
                            <span className="register-error-text">
                                {errors.password}
                            </span>
                        }
                    </div>
                    <div className="register-form-group">
                        <label className="register-label" htmlFor="confirmPassword">
                            Confirm Password
                        </label>
                        <input
                            id="confirmPassword"
                            type="password"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            required
                            className="register-input"
                        />
                        {errors.confirmPassword &&
                            <span className="register-error-text">
                                {errors.confirmPassword}
                            </span>
                        }
                    </div>
                    <button className="register-submit-btn" onClick={handleSubmit}>
                        {submitting ? 'Creating account...' : 'Create Account'}
                    </button>
                </form>
                <div className="register-login-link-wrapper">
                    <p className="register-login-link-text">
                        Already have an account?
                        <Link className="register-login-link" to="/login">
                            Sign in
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default RegisterPage;