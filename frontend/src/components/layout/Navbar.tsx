import { useNavigate } from 'react-router-dom';
import { LogOut, User as UserIcon } from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import './Navbar.css';

export const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

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
              {user.full_name}
            </span>
            <button onClick={() => void logout().then(() => navigate('/login'))} className="btn-logout" aria-label="Sign out">
              <LogOut size={16} />
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
