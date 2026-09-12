import React from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, User as UserIcon } from 'lucide-react';
import './Navbar.css';

export const Navbar = () => {
  const { user, logout } = useAuth();

  return (
    <header className="navbar">
      <div className="navbar-brand">
        <h2>Smart Form AI</h2>
      </div>
      <div className="navbar-actions">
        {user && (
          <div className="user-menu">
            <span className="user-name">
              <UserIcon size={16} />
              {user.name}
            </span>
            <button onClick={logout} className="btn-logout" aria-label="Logout">
              <LogOut size={16} />
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
