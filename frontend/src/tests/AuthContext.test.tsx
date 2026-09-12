import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import React, { useEffect } from 'react';

// Helper component to test AuthContext
const TestComponent = () => {
  const { user, token, isLoading, login, logout } = useAuth();

  if (isLoading) return <div>Loading...</div>;

  return (
    <div>
      <div data-testid="user-name">{user ? user.name : 'No User'}</div>
      <div data-testid="token">{token ? 'Has Token' : 'No Token'}</div>
      <button onClick={() => login('fake-token', { id: '1', name: 'Test User', email: 'test@example.com' })}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    globalThis.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('provides null user initially when no token exists', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('user-name')).toHaveTextContent('No User');
      expect(screen.getByTestId('token')).toHaveTextContent('No Token');
    });
  });

  it('fetches user if token exists in localStorage', async () => {
    localStorage.setItem('token', 'valid-token');
    
    (globalThis.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ id: '1', name: 'Saved User', email: 'saved@example.com' })
    });

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('user-name')).toHaveTextContent('Saved User');
      expect(screen.getByTestId('token')).toHaveTextContent('Has Token');
    });
    
    expect(globalThis.fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/auth/me'), expect.objectContaining({
      headers: { Authorization: 'Bearer valid-token' }
    }));
  });

  it('logs user in and updates context', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('user-name')).toHaveTextContent('No User'));

    screen.getByText('Login').click();

    await waitFor(() => {
      expect(screen.getByTestId('user-name')).toHaveTextContent('Test User');
      expect(screen.getByTestId('token')).toHaveTextContent('Has Token');
      expect(localStorage.getItem('token')).toBe('fake-token');
    });
  });

  it('logs user out and clears context', async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );

    await waitFor(() => expect(screen.getByTestId('user-name')).toHaveTextContent('No User'));
    
    screen.getByText('Login').click();
    await waitFor(() => expect(screen.getByTestId('user-name')).toHaveTextContent('Test User'));

    screen.getByText('Logout').click();
    await waitFor(() => {
      expect(screen.getByTestId('user-name')).toHaveTextContent('No User');
      expect(localStorage.getItem('token')).toBeNull();
    });
  });
});
