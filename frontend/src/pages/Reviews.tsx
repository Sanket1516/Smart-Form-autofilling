import React, { useEffect, useState } from 'react';
import { reviewsApi } from '../services/api';
import { ReviewCard } from '../components/reviews/ReviewCard';
import { AlertTriangle, CheckCircle, FileQuestion } from 'lucide-react';
import { Button } from '../components/ui/Button';
import './Reviews.css';

export const Reviews = () => {
  const [reviews, setReviews] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReviews();
  }, []);

  const fetchReviews = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await reviewsApi.getPendingReviews();
      setReviews(data);
    } catch (err: any) {
      setError('Failed to load pending reviews.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDecision = async (id: string, decision: 'confirm' | 'edit' | 'reject' | 'skip', newValue?: string) => {
    try {
      await reviewsApi.submitDecision(id, decision, newValue);
      // Remove from list
      setReviews(prev => prev.filter(r => r.review_id !== id));
    } catch (err) {
      alert('Failed to submit decision.');
      throw err;
    }
  };

  if (isLoading) {
    return <div className="reviews-loading">Loading pending reviews...</div>;
  }

  if (error) {
    return (
      <div className="reviews-error">
        <AlertTriangle size={32} />
        <p>{error}</p>
        <Button onClick={fetchReviews}>Retry</Button>
      </div>
    );
  }

  return (
    <div className="reviews-page">
      <div className="page-header">
        <div className="page-title-section">
          <FileQuestion size={28} className="page-icon" />
          <div>
            <h1>Field Reviews</h1>
            <p>Resolve conflicting or low-confidence autofill suggestions.</p>
          </div>
        </div>
      </div>

      <div className="reviews-content">
        {reviews.length === 0 ? (
          <div className="empty-state">
            <CheckCircle size={48} className="text-success" />
            <h3>All Caught Up!</h3>
            <p>There are no pending reviews at this time.</p>
          </div>
        ) : (
          <div className="reviews-list">
            {reviews.map(review => (
              <ReviewCard
                key={review.review_id}
                id={review.review_id}
                concept={review.concept}
                suggestedValue={review.suggested_value}
                confidence={review.confidence}
                reason={review.reason}
                sources={review.sources}
                onDecision={handleDecision}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
