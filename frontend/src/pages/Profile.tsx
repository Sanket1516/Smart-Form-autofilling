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
    // In a full implementation, this would open a modal to edit the fact via correction API
    alert(`Editing concept: ${fact.concept} (Current: ${fact.value})`);
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
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
