import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, ApiError } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import './Auth.css';

export const Register = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!name.trim()) return setError('Name is required.');
    if (!/\S+@\S+\.\S+/.test(email)) return setError('Please enter a valid email address.');
    if (password.length < 8) return setError('Password must be at least 8 characters long.');
    if (/^\d+$/.test(password) || /^[A-Za-z]+$/.test(password)) {
      return setError('Use letters together with numbers or symbols.');
    }
    if (new TextEncoder().encode(password).length > 72) return setError('Password is too long (72 bytes maximum).');
    if (password !== confirmPassword) return setError('Passwords do not match.');

    setIsLoading(true);
    try {
      await authApi.register(name.trim(), email.trim(), password, confirmPassword);
      await login(email.trim(), password);
      navigate('/dashboard');
    } catch (err) {
      const apiError = err as ApiError;
      setError(apiError.status === 409 ? 'An account with this email already exists.' : apiError.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <h2>Create your account</h2>
          <p className="text-secondary">Your documents and profile stay private to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {error && <div className="auth-error-banner" role="alert">{error}</div>}
          <Input label="Full name" name="full_name" value={name} onChange={(e) => setName(e.target.value)}
            required autoComplete="name" />
          <Input type="email" label="Email" name="email" value={email} onChange={(e) => setEmail(e.target.value)}
            required autoComplete="email" />
          <Input type="password" label="Password" name="password" value={password}
            onChange={(e) => setPassword(e.target.value)} required autoComplete="new-password"
            helpText="At least 8 characters, with letters and numbers or symbols." />
          <Input type="password" label="Confirm password" name="confirm_password" value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)} required autoComplete="new-password" />
          <Button type="submit" className="auth-submit-btn" isLoading={isLoading}>Create account</Button>
        </form>
        <div className="auth-footer">
          <p>Already have an account? <Link to="/login">Sign in</Link></p>
        </div>
      </div>
    </div>
  );
};
