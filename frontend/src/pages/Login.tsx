import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth, User } from '../contexts/AuthContext';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import './Auth.css';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const validateEmail = (email: string) => {
    return /\S+@\S+\.\S+/.test(email);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!validateEmail(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    
    if (!password) {
      setError('Password is required.');
      return;
    }

    setIsLoading(true);
    
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const res = await fetch(`${baseUrl}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      
      if (res.ok) {
        const json = await res.json();
        const authData = json.data || json;
        const accessToken = authData.access_token;
        const userObj = authData.user;

        if (accessToken && userObj) {
          login(accessToken, userObj);
          navigate('/dashboard');
        } else if (accessToken) {
          const meRes = await fetch(`${baseUrl}/api/v1/auth/me`, {
            headers: { Authorization: `Bearer ${accessToken}` }
          });
          
          if (meRes.ok) {
            const meJson = await meRes.json();
            const user: User = meJson.data || meJson;
            login(accessToken, user);
            navigate('/dashboard');
          } else {
            setError('Failed to load user profile.');
          }
        } else {
          setError('Invalid login response from server.');
        }
      } else if (res.status === 401 || res.status === 400) {
        setError('Invalid credentials.');
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } catch (err) {
      setError('Network error. Please check your connection and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Welcome Back</h2>
          <p className="text-secondary">Sign in to your account to continue</p>
        </div>
        
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {error && <div className="auth-error-banner" role="alert">{error}</div>}
          
          <Input
            type="email"
            label="Email"
            name="email"
            placeholder="name@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
          />
          
          <Input
            type="password"
            label="Password"
            name="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
          
          <Button type="submit" className="auth-submit-btn" isLoading={isLoading}>
            Login
          </Button>
        </form>
        
        <div className="auth-footer">
          <p>
            <a href="#">Forgot password?</a>
          </p>
          <p>
            Don't have an account? <Link to="/register">Register</Link>
          </p>
        </div>
      </div>
    </div>
  );
};
