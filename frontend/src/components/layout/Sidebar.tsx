import { NavLink, useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, Brain, FileQuestion, FileText, LayoutDashboard, LogOut, MessageSquareText, Settings, User,
  type LucideIcon,
} from 'lucide-react';
import { useAuth } from '../../contexts/AuthContext';
import { Logo } from '../ui/Brand';
import './Sidebar.css';

const SECTIONS: Array<{ title?: string; links: Array<{ to: string; label: string; icon: LucideIcon }> }> = [
  { links: [{ to: '/dashboard', label: 'Overview', icon: LayoutDashboard }] },
  {
    title: 'Your information',
    links: [
      { to: '/documents', label: 'Documents', icon: FileText },
      { to: '/profile', label: 'Profile', icon: User },
      { to: '/discovered-facts', label: 'Discovered facts', icon: Brain },
    ],
  },
  {
    title: 'Needs you',
    links: [
      { to: '/conflicts', label: 'Conflicts', icon: AlertTriangle },
      { to: '/reviews', label: 'Field reviews', icon: FileQuestion },
    ],
  },
  {
    title: 'Tools',
    links: [
      { to: '/ask', label: 'Ask your documents', icon: MessageSquareText },
      { to: '/activity', label: 'Activity', icon: Activity },
      { to: '/settings', label: 'Settings', icon: Settings },
    ],
  },
];

export const Sidebar = ({ id, open }: { id: string; open: boolean }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <aside id={id} className={`sidebar ${open ? 'open' : ''}`} aria-label="Main">
      <div className="sidebar-brand"><Logo /></div>
      <nav className="sidebar-nav">
        {SECTIONS.map((section, index) => (
          <div key={section.title ?? index} className="sidebar-section">
            {section.title && <p className="sidebar-heading">{section.title}</p>}
            <ul>
              {section.links.map(({ to, label, icon: Icon }) => (
                <li key={to}>
                  <NavLink to={to} className={({ isActive }) => (isActive ? 'active' : '')}>
                    <Icon size={16} aria-hidden="true" />
                    {label}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
      {user && (
        <div className="sidebar-user">
          <span className="avatar" aria-hidden="true">{(user.full_name || user.email).trim().charAt(0).toUpperCase()}</span>
          <span className="sidebar-user-text">
            <span className="sidebar-user-name">{user.full_name}</span>
            <span className="sidebar-user-email">{user.email}</span>
          </span>
          <button className="icon-button" onClick={() => void logout().then(() => navigate('/login'))}
            aria-label="Sign out" title="Sign out">
            <LogOut size={16} aria-hidden="true" />
          </button>
        </div>
      )}
    </aside>
  );
};
