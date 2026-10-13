import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { Login } from '../pages/Login';
import { Register } from '../pages/Register';
import { mockApi, renderApp, USER } from './helpers';

afterEach(() => vi.unstubAllGlobals());

describe('login', () => {
  it('signs in, stores the token and goes to the dashboard', async () => {
    const { calls } = mockApi({
      'POST /auth/login': () => ({ data: { access_token: 'new-token', user: USER } }),
    });
    renderApp(<Login />, { path: '/', signedIn: false });
    fireEvent.change(screen.getByLabelText(/Email/), { target: { value: 'avery@example.com' } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: 'Str0ng-Passw0rd!' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument();
    expect(localStorage.getItem('token')).toBe('new-token');
    expect(calls[0].body).toEqual({ email: 'avery@example.com', password: 'Str0ng-Passw0rd!' });
  });

  it('shows a clear message for wrong credentials and rate limiting', async () => {
    mockApi({ 'POST /auth/login': () => ({ status: 401, error: { code: 'INVALID_CREDENTIALS', message: 'x' } }) });
    renderApp(<Login />, { signedIn: false });
    fireEvent.change(screen.getByLabelText(/Email/), { target: { value: 'a@example.com' } });
    fireEvent.change(screen.getByLabelText(/Password/), { target: { value: 'wrong' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Incorrect email or password.');

    mockApi({ 'POST /auth/login': () => ({ status: 429, error: { code: 'RATE_LIMITED', message: 'x' } }) });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Too many attempts'));
  });

  it('validates input before calling the server', async () => {
    const { fetchMock } = mockApi({});
    renderApp(<Login />, { signedIn: false });
    fireEvent.change(screen.getByLabelText(/Email/), { target: { value: 'not-an-email' } });
    fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('valid email');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('a stored but expired token signs the user out', async () => {
    mockApi({ 'GET /auth/me': () => ({ status: 401, error: { code: 'UNAUTHORIZED', message: 'x' } }) });
    renderApp(<Login />);
    await waitFor(() => expect(localStorage.getItem('token')).toBeNull());
  });
});

describe('register', () => {
  const fill = (password: string, confirm = password) => {
    fireEvent.change(screen.getByLabelText(/Full name/), { target: { value: 'Avery Example' } });
    fireEvent.change(screen.getByLabelText(/^Email/), { target: { value: 'avery@example.com' } });
    fireEvent.change(screen.getByLabelText(/^Password/), { target: { value: password } });
    fireEvent.change(screen.getByLabelText(/Confirm password/), { target: { value: confirm } });
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }));
  };

  it('registers and signs in', async () => {
    const { calls } = mockApi({
      'POST /auth/register': () => ({ status: 201, data: USER }),
      'POST /auth/login': () => ({ data: { access_token: 't', user: USER } }),
    });
    renderApp(<Register />, { signedIn: false });
    fill('Str0ng-Passw0rd!');
    expect(await screen.findByText('Dashboard page')).toBeInTheDocument();
    expect(calls.map((c) => c.key)).toEqual(['POST /auth/register', 'POST /auth/login']);
  });

  it('rejects weak or mismatched passwords and shows duplicate-email errors', async () => {
    mockApi({ 'POST /auth/register': () => ({ status: 409, error: { code: 'EMAIL_ALREADY_EXISTS', message: 'x' } }) });
    renderApp(<Register />, { signedIn: false });
    fill('onlyletters');
    expect(await screen.findByRole('alert')).toHaveTextContent('letters together with numbers');
    fill('Str0ng-Passw0rd!', 'different1!');
    expect(await screen.findByRole('alert')).toHaveTextContent('do not match');
    fill('Str0ng-Passw0rd!');
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('already exists'));
  });
});
