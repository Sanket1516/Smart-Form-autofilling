import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConfidenceBadge } from '../components/ui/ConfidenceBadge';
import React from 'react';

describe('ConfidenceBadge', () => {
  it('renders high confidence badge correctly', () => {
    render(<ConfidenceBadge level="high" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('High confidence');
    expect(badge).toHaveClass('badge-success');
    expect(badge).toHaveAttribute('aria-label', 'High confidence');
  });

  it('renders medium confidence badge correctly', () => {
    render(<ConfidenceBadge level="medium" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Review recommended');
    expect(badge).toHaveClass('badge-warning');
  });

  it('renders low confidence badge correctly', () => {
    render(<ConfidenceBadge level="low" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Confirmation required');
    expect(badge).toHaveClass('badge-info');
  });

  it('renders conflict badge correctly', () => {
    render(<ConfidenceBadge level="conflict" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Conflicting information');
    expect(badge).toHaveClass('badge-error');
  });

  it('allows overriding text', () => {
    render(<ConfidenceBadge level="high" text="Verified" />);
    const badge = screen.getByRole('status');
    expect(badge).toHaveTextContent('Verified');
    expect(badge).toHaveAttribute('aria-label', 'Verified');
  });
});
