import React, { ButtonHTMLAttributes } from 'react';
import './Button.css';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  isLoading?: boolean;
}

export const Button = ({ children, variant = 'primary', isLoading, disabled, className, ...props }: ButtonProps) => {
  return (
    <button
      className={`btn btn-${variant} ${className || ''}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading ? <span className="spinner"></span> : children}
    </button>
  );
};
