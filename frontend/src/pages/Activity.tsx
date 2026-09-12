import React from 'react';
import { Activity as ActivityIcon, Clock, Edit } from 'lucide-react';
import './Activity.css';

export const Activity = () => {
  // Stubbed activity history data
  const activities = [
    { id: 1, type: 'form_session', title: 'Autofilled "Tax Return 2026"', date: '2 hours ago', icon: <Edit size={16} /> },
    { id: 2, type: 'document', title: 'Processed "W2_Form_2025.pdf"', date: '1 day ago', icon: <ActivityIcon size={16} /> },
    { id: 3, type: 'review', title: 'Resolved 3 field conflicts', date: '2 days ago', icon: <Clock size={16} /> }
  ];

  return (
    <div className="activity-page">
      <div className="page-header">
        <div className="page-title-section">
          <ActivityIcon size={28} className="page-icon" />
          <div>
            <h1>Activity & History</h1>
            <p>Your recent form sessions, document processing, and system events.</p>
          </div>
        </div>
      </div>

      <div className="activity-content">
        <div className="timeline-container">
          {activities.length === 0 ? (
            <div className="empty-state">
              <Clock size={48} />
              <h3>No Activity Yet</h3>
              <p>Your history will appear here once you start using the system.</p>
            </div>
          ) : (
            <ul className="timeline">
              {activities.map(act => (
                <li key={act.id} className="timeline-item">
                  <div className="timeline-icon">{act.icon}</div>
                  <div className="timeline-content">
                    <h4>{act.title}</h4>
                    <span className="timeline-date">{act.date}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};
