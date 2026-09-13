import React, { useEffect, useState } from 'react';
import { factsApi, profileApi } from '../services/api';
import { FactCard } from '../components/profile/FactCard';
import { User, BookOpen, AlertCircle } from 'lucide-react';
import { Button } from '../components/ui/Button';
import './Profile.css';

export const Profile = () => {
  const [facts, setFacts] = useState<any[]>([]);
  const [profile, setProfile] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [editingFact, setEditingFact] = useState<any>(null);
  const [editValue, setEditValue] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [factsData, profileData] = await Promise.all([
        factsApi.getFacts(),
        profileApi.getProfile()
      ]);
      setFacts(factsData);
      setProfile(profileData);
    } catch (err: any) {
      setError('Failed to load profile knowledge base.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleEditFact = (fact: any) => {
    setEditingFact(fact);
    let initialValue = fact.value;
    if (typeof initialValue === 'object' && initialValue !== null) {
      initialValue = Array.isArray(initialValue) ? initialValue.join(', ') : JSON.stringify(initialValue);
    }
    setEditValue(initialValue || '');
  };

  const handleSaveEdit = async () => {
    if (!editingFact) return;
    try {
      await factsApi.updateFact(editingFact.fact_id || editingFact.id, editValue);
      setEditingFact(null);
      fetchData();
    } catch (err: any) {
      alert(`Error updating fact: ${err.message}`);
    }
  };

  const handleDeleteFact = async (fact: any) => {
    if (confirm(`Are you sure you want to delete ${fact.concept}?`)) {
      try {
        await factsApi.deleteFact(fact.fact_id || fact.id);
        fetchData();
      } catch (err: any) {
        alert(`Error deleting fact: ${err.message}`);
      }
    }
  };

  if (isLoading) {
    return <div className="profile-loading">Loading knowledge base...</div>;
  }

  if (error) {
    return (
      <div className="profile-error">
        <AlertCircle size={32} />
        <p>{error}</p>
        <Button onClick={fetchData}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="page-header">
        <div className="page-title-section">
          <BookOpen size={28} className="page-icon" />
          <div>
            <h1>Knowledge Profile</h1>
            <p>Your extracted facts and knowledge base for autofilling forms.</p>
          </div>
        </div>
      </div>

      <div className="profile-content">
        <div className="facts-section">
          <h2>Extracted Facts</h2>
          {facts.length === 0 ? (
            <div className="empty-state">
              <User size={48} />
              <h3>No facts extracted yet</h3>
              <p>Upload documents to start building your knowledge base.</p>
            </div>
          ) : (
            <div className="facts-grid">
              {facts.map((fact: any) => (
                <FactCard
                  key={fact.fact_id || fact.concept}
                  concept={fact.concept}
                  value={fact.value}
                  confidence={fact.confidence}
                  sourceDocument={fact.source_document_id}
                  onEdit={() => handleEditFact(fact)}
                  onDelete={() => handleDeleteFact(fact)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {editingFact && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Edit Fact: {editingFact.concept.replace(/_/g, ' ')}</h3>
            <div className="form-group" style={{marginTop: '1rem'}}>
              <input 
                type="text" 
                value={editValue} 
                onChange={(e) => setEditValue(e.target.value)} 
                className="filter-input"
                style={{width: '100%', padding: '0.5rem'}}
              />
            </div>
            <div className="modal-actions" style={{display: 'flex', gap: '1rem', marginTop: '1rem', justifyContent: 'flex-end'}}>
              <Button variant="outline" onClick={() => setEditingFact(null)}>Cancel</Button>
              <Button onClick={handleSaveEdit}>Save</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
