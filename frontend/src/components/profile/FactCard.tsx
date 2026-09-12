import React from 'react';
import { ConfidenceBadge, ConfidenceLevel } from '../ui/ConfidenceBadge';
import { Edit2, ExternalLink } from 'lucide-react';
import { Button } from '../ui/Button';
import './FactCard.css';

interface FactCardProps {
  concept: string;
  value: string;
  sourceDocument?: string;
  confidence: number;
  onEdit: () => void;
}

export const FactCard: React.FC<FactCardProps> = ({ 
  concept, 
  value, 
  sourceDocument, 
  confidence, 
  onEdit 
}) => {
  // Determine confidence level mapping
  let level: ConfidenceLevel = 'low';
  if (confidence >= 0.9) level = 'high';
  else if (confidence >= 0.7) level = 'medium';

  return (
    <div className="fact-card">
      <div className="fact-card-header">
        <h4 className="fact-concept">{concept.replace(/_/g, ' ')}</h4>
        <div className="fact-actions">
          <Button variant="outline" size="sm" onClick={onEdit} className="edit-btn">
            <Edit2 size={14} />
            <span>Edit</span>
          </Button>
        </div>
      </div>
      
      <div className="fact-card-body">
        <p className="fact-value">{value}</p>
      </div>
      
      <div className="fact-card-footer">
        <ConfidenceBadge level={level} text={`${Math.round(confidence * 100)}% Confidence`} />
        {sourceDocument && (
          <div className="fact-source" title={`Extracted from ${sourceDocument}`}>
            <ExternalLink size={14} />
            <span className="source-name">{sourceDocument}</span>
          </div>
        )}
      </div>
    </div>
  );
};
