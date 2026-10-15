import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ApiError } from '../services/api';
import { Input } from '../components/ui/Input';
import { Button } from '../components/ui/Button';
import { AuthLayout } from '../components/layout/AuthLayout';

export const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setError('Password is required.');
      return;
    }
    setIsLoading(true);
    try {
      await login(email.trim(), password);
      navigate('/dashboard');
    } catch (err) {
      const apiError = err as ApiError;
      if (apiError.status === 401) setError('Incorrect email or password.');
      else if (apiError.status === 429) setError('Too many attempts. Wait a minute and try again.');
      else setError(apiError.message || 'Sign-in failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <AuthLayout title="Sign in to Smart Form" subtitle="Manage your documents and the profile used to fill forms."
      footer={<p>New to Smart Form? <Link to="/register">Create an account</Link></p>}>
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {error && <div className="auth-error-banner" role="alert">{error}</div>}
          <Input type="email" label="Email" name="email" placeholder="name@example.com" value={email}
            onChange={(e) => setEmail(e.target.value)} required autoComplete="email" />
          <Input type="password" label="Password" name="password" placeholder="Enter your password" value={password}
            onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
          <Button type="submit" className="auth-submit-btn" isLoading={isLoading}>Sign in</Button>
        </form>
    </AuthLayout>
  );
};
