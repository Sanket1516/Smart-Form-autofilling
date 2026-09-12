import React from 'react';
import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { Sidebar } from './Sidebar';
import './AppShell.css';

export const AppShell = () => {
  return (
    <div className="app-shell">
      <Navbar />
      <div className="app-shell-body">
        <Sidebar />
        <main className="app-shell-main">
          <div className="main-content">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
};
