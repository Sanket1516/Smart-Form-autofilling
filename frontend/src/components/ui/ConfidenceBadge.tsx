import React from 'react';
import { CheckCircle2, AlertTriangle, HelpCircle, AlertOctagon } from 'lucide-react';
import './ConfidenceBadge.css';

export type ConfidenceLevel = 'high' | 'medium' | 'low' | 'conflict';

interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  text?: string;
}

export const ConfidenceBadge = ({ level, text }: ConfidenceBadgeProps) => {
  const config = {
    high: {
      icon: <CheckCircle2 size={14} />,
      defaultText: 'High confidence',
      className: 'badge-success'
    },
    medium: {
      icon: <AlertTriangle size={14} />,
      defaultText: 'Review recommended',
      className: 'badge-warning'
    },
    low: {
      icon: <HelpCircle size={14} />,
      defaultText: 'Confirmation required',
      className: 'badge-info'
    },
    conflict: {
      icon: <AlertOctagon size={14} />,
      defaultText: 'Conflicting information',
      className: 'badge-error'
    }
  };

  const { icon, defaultText, className } = config[level];

  return (
    <span className={`confidence-badge ${className}`} role="status" aria-label={text || defaultText}>
      {icon}
      <span>{text || defaultText}</span>
    </span>
  );
};
