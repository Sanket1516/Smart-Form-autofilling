import React, { useState } from 'react';
import { ConfidenceBadge, ConfidenceLevel } from '../ui/ConfidenceBadge';
import { Button } from '../ui/Button';
import { Check, X, Edit2, FastForward } from 'lucide-react';
import './ReviewCard.css';

interface ReviewCardProps {
  id: string;
  concept: string;
  suggestedValue: string;
  confidence: number;
  reason: string;
  sources: Array<{ document_id: string }>;
  onDecision: (id: string, decision: 'confirm' | 'edit' | 'reject' | 'skip', newValue?: string) => Promise<void>;
}

export const ReviewCard: React.FC<ReviewCardProps> = ({
  id,
  concept,
  suggestedValue,
  confidence,
  reason,
  sources,
  onDecision
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(suggestedValue);
  const [isSubmitting, setIsSubmitting] = useState(false);

  let level: ConfidenceLevel = 'low';
  if (confidence >= 0.9) level = 'high';
  else if (confidence >= 0.7) level = 'medium';

  const handleDecision = async (decision: 'confirm' | 'edit' | 'reject' | 'skip') => {
    setIsSubmitting(true);
    try {
      await onDecision(id, decision, decision === 'edit' ? editValue : undefined);
    } finally {
      setIsSubmitting(false);
      setIsEditing(false);
    }
  };

  return (
    <div className="review-card">
      <div className="review-card-header">
        <div>
          <h4 className="review-concept">{concept.replace(/_/g, ' ')}</h4>
          <p className="review-reason">{reason}</p>
        </div>
        <ConfidenceBadge level={level} text={`${Math.round(confidence * 100)}% Confidence`} />
      </div>

      <div className="review-card-body">
        {isEditing ? (
          <div className="review-edit-container">
            <input 
              type="text" 
              className="review-edit-input" 
              value={editValue} 
              onChange={(e) => setEditValue(e.target.value)}
              autoFocus
            />
            <div className="review-edit-actions">
              <Button size="sm" onClick={() => handleDecision('edit')} isLoading={isSubmitting}>Save</Button>
              <Button variant="outline" size="sm" onClick={() => setIsEditing(false)} disabled={isSubmitting}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="review-value-container">
            <p className="review-value">{suggestedValue}</p>
          </div>
        )}
      </div>

      {!isEditing && (
        <div className="review-actions">
          <Button 
            variant="primary" 
            className="action-btn confirm" 
            onClick={() => handleDecision('confirm')}
            isLoading={isSubmitting}
          >
            <Check size={16} /> Confirm
          </Button>
          <Button 
            variant="outline" 
            className="action-btn edit" 
            onClick={() => setIsEditing(true)}
            disabled={isSubmitting}
          >
            <Edit2 size={16} /> Edit
          </Button>
          <Button 
            variant="outline" 
            className="action-btn reject" 
            onClick={() => handleDecision('reject')}
            isLoading={isSubmitting}
          >
            <X size={16} /> Reject
          </Button>
          <Button 
            variant="outline" 
            className="action-btn skip" 
            onClick={() => handleDecision('skip')}
            disabled={isSubmitting}
          >
            <FastForward size={16} /> Skip
          </Button>
        </div>
      )}
      
      {sources && sources.length > 0 && (
        <div className="review-sources">
          <span className="source-label">Sources:</span>
          {sources.map((s, idx) => (
            <span key={idx} className="source-id">{s.document_id}</span>
          ))}
        </div>
      )}
    </div>
  );
};
