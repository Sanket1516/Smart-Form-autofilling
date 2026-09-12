import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, FileText, User, Activity, Settings } from 'lucide-react';
import './Sidebar.css';

export const Sidebar = () => {
  return (
    <aside className="sidebar">
      <nav className="sidebar-nav">
        <ul>
          <li>
            <NavLink to="/dashboard" className={({ isActive }) => isActive ? 'active' : ''}>
              <LayoutDashboard size={20} />
              Dashboard
            </NavLink>
          </li>
          <li>
            <NavLink to="/documents" className={({ isActive }) => isActive ? 'active' : ''}>
              <FileText size={20} />
              Documents
            </NavLink>
          </li>
          <li>
            <NavLink to="/profile" className={({ isActive }) => isActive ? 'active' : ''}>
              <User size={20} />
              My Profile
            </NavLink>
          </li>
          <li>
            <NavLink to="/activity" className={({ isActive }) => isActive ? 'active' : ''}>
              <Activity size={20} />
              Activity / History
            </NavLink>
          </li>
          <li>
            <NavLink to="/settings" className={({ isActive }) => isActive ? 'active' : ''}>
              <Settings size={20} />
              Settings
            </NavLink>
          </li>
        </ul>
      </nav>
    </aside>
  );
};
