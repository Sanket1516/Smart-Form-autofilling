import React, { useState } from 'react';
import { Settings as SettingsIcon, Shield, Trash2, Key, Bell, AppWindow } from 'lucide-react';
import { Button } from '../components/ui/Button';
import './Settings.css';

export const Settings = () => {
  const [deleteDataConfirm, setDeleteDataConfirm] = useState(false);
  const [deleteAccountConfirm, setDeleteAccountConfirm] = useState(false);

  const handleDeleteData = () => {
    if (!deleteDataConfirm) {
      setDeleteDataConfirm(true);
      return;
    }
    // Delete data logic
    alert('All user data (documents, facts, reviews) deleted successfully.');
    setDeleteDataConfirm(false);
  };

  const handleDeleteAccount = () => {
    if (!deleteAccountConfirm) {
      setDeleteAccountConfirm(true);
      return;
    }
    // Delete account logic
    alert('Account deleted successfully.');
    setDeleteAccountConfirm(false);
  };

  return (
    <div className="settings-page">
      <div className="page-header">
        <div className="page-title-section">
          <SettingsIcon size={28} className="page-icon" />
          <div>
            <h1>Settings</h1>
            <p>Manage your account, privacy, and extension preferences.</p>
          </div>
        </div>
      </div>

      <div className="settings-content">
        <div className="settings-section">
          <h2><AppWindow size={20} /> Extension Preferences</h2>
          <div className="settings-card">
            <div className="setting-item">
              <div>
                <h4>Auto-fill suggestions</h4>
                <p>Show inline suggestions when visiting supported web forms.</p>
              </div>
              <label className="toggle-switch">
                <input type="checkbox" defaultChecked />
                <span className="slider round"></span>
              </label>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h2><Shield size={20} /> Privacy & Data</h2>
          <div className="settings-card">
            <div className="setting-item">
              <div>
                <h4>Clear all data</h4>
                <p>Permanently delete all uploaded documents and extracted facts. This cannot be undone.</p>
              </div>
              <div className="destructive-action-container">
                {deleteDataConfirm && (
                  <p className="confirmation-warning">Are you absolutely sure?</p>
                )}
                <Button 
                  variant="outline" 
                  className="btn-danger" 
                  onClick={handleDeleteData}
                >
                  <Trash2 size={16} style={{ marginRight: '8px' }} />
                  {deleteDataConfirm ? 'Confirm Deletion' : 'Delete Data'}
                </Button>
                {deleteDataConfirm && (
                  <Button variant="outline" onClick={() => setDeleteDataConfirm(false)}>Cancel</Button>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="settings-section">
          <h2><Key size={20} /> Account Management</h2>
          <div className="settings-card">
            <div className="setting-item">
              <div>
                <h4>Delete Account</h4>
                <p>Permanently delete your account and all associated data.</p>
              </div>
              <div className="destructive-action-container">
                {deleteAccountConfirm && (
                  <p className="confirmation-warning">Are you absolutely sure?</p>
                )}
                <Button 
                  variant="outline" 
                  className="btn-danger" 
                  onClick={handleDeleteAccount}
                >
                  <Trash2 size={16} style={{ marginRight: '8px' }} />
                  {deleteAccountConfirm ? 'Confirm Account Deletion' : 'Delete Account'}
                </Button>
                {deleteAccountConfirm && (
                  <Button variant="outline" onClick={() => setDeleteAccountConfirm(false)}>Cancel</Button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
