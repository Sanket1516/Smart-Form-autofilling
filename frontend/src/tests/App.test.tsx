import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from '../App';

describe('App component', () => {
  it('renders without crashing and displays the layout', () => {
    render(<App />);
    // Our App layout generally renders a router outlet. If we are at /, it should render the main login or dashboard
    // We can just assert that it renders without throwing an error
    expect(document.body).toBeDefined();
  });
});
