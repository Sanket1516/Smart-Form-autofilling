import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { Button } from '../components/ui/Button';
import { FileText, Database, Activity, Clock } from 'lucide-react';
import './Dashboard.css';

export const Dashboard = () => {
  const { user } = useAuth();

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Welcome back{user?.name ? `, ${user.name}` : ''}!</h1>
        <p className="text-secondary">Here's an overview of your Smart Form AI activity.</p>
      </header>

      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-icon">
            <FileText size={24} />
          </div>
          <div className="stat-content">
            <h3>Documents</h3>
            <p className="stat-value">5 <span className="stat-label">processed</span></p>
            <p className="stat-subtext">1 processing</p>
          </div>
        </div>
        
        <div className="stat-card">
          <div className="stat-icon">
            <Database size={24} />
          </div>
          <div className="stat-content">
            <h3>Knowledge Profile</h3>
            <p className="stat-value">42 <span className="stat-label">facts</span></p>
          </div>
        </div>
      </div>

      <div className="dashboard-sections">
        <section className="dashboard-section recent-activity">
          <h2>Recent Activity</h2>
          <hr className="section-divider" />
          <ul className="activity-list">
            <li className="activity-item">
              <div className="activity-icon completed">
                <Activity size={16} />
              </div>
              <div className="activity-details">
                <h4>Job Application Form</h4>
                <span className="activity-status text-success">Completed</span>
              </div>
              <div className="activity-time">
                <Clock size={14} />
                <span>2 hours ago</span>
              </div>
            </li>
            <li className="activity-item">
              <div className="activity-icon pending">
                <Activity size={16} />
              </div>
              <div className="activity-details">
                <h4>Scholarship Form</h4>
                <span className="activity-status text-warning">Needs Review</span>
              </div>
              <div className="activity-time">
                <Clock size={14} />
                <span>Yesterday</span>
              </div>
            </li>
          </ul>
        </section>

        <section className="dashboard-section quick-actions">
          <h2>Quick Actions</h2>
          <hr className="section-divider" />
          <div className="action-buttons">
            <Button variant="primary">Upload Document</Button>
            <Button variant="secondary">Open Extension</Button>
            <Button variant="secondary">Review Pending Items</Button>
          </div>
        </section>
      </div>
    </div>
  );
};
