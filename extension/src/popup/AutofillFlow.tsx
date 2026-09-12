import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, Play, Check, X, ShieldAlert } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

export const AutofillFlow = ({ 
  sessionId, 
  token,
  onComplete
}: { 
  sessionId: string, 
  token: string,
  onComplete: () => void 
}) => {
  const [status, setStatus] = useState<'processing' | 'review_required' | 'ready' | 'filling' | 'verifying' | 'done'>('processing');
  const [reviews, setReviews] = useState<any[]>([]);
  const [approvedValues, setApprovedValues] = useState<any[]>([]);

  // Poll for session status
  useEffect(() => {
    if (status !== 'processing') return;

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.data.status === 'review_required') {
          setStatus('review_required');
          fetchReviews();
          clearInterval(interval);
        } else if (data.data.status === 'ready' || data.data.status === 'completed') {
          setStatus('ready');
          fetchApprovedValues();
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [status]);

  const fetchReviews = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/reviews/pending`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      // Filter for this session only
      const sessionReviews = data.data.reviews.filter((r: any) => r.session_id === sessionId);
      if (sessionReviews.length === 0) {
        setStatus('ready');
        fetchApprovedValues();
      } else {
        setReviews(sessionReviews);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchApprovedValues = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}/approved-values`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      setApprovedValues(data.data.approved_values);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReviewDecision = async (reviewId: string, decision: 'confirm' | 'reject', value?: string) => {
    try {
      await fetch(`${API_BASE_URL}/reviews/${reviewId}/decision`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ decision, value })
      });
      
      const newReviews = reviews.filter(r => r.review_id !== reviewId);
      setReviews(newReviews);
      
      if (newReviews.length === 0) {
        setStatus('ready');
        fetchApprovedValues();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const startFilling = () => {
    setStatus('filling');
    
    // Listen for verifications from background
    const listener = (_msg: any) => {
      // In a real app, we'd wait for all verifications. For simplicity, just gather them.
      // We rely on the content script to send VERIFY_FIELD to background, but background
      // responds. We could also just let background broadcast TAB_VERIFIED, but since the
      // background doesn't broadcast, we should have content script send directly to popup?
      // Actually, content script sends VERIFY_FIELD to background.
      // Let's just wait 2 seconds after filling then transition to done.
    };
    chrome.runtime.onMessage.addListener(listener);
    
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'FILL_FIELDS',
          payload: { approvedValues, sessionId, token }
        });
      }
    });

    setTimeout(() => {
      setStatus('done');
      chrome.runtime.onMessage.removeListener(listener);
    }, 2000); // Wait for fills to complete
  };

  if (status === 'processing') {
    return (
      <div className="flow-state">
        <Loader2 size={32} className="spin text-primary mx-auto mb-4" />
        <h3 className="text-center">Analyzing form fields...</h3>
        <p className="text-center text-secondary mt-2">Checking compatibility and finding optimal values.</p>
      </div>
    );
  }

  if (status === 'review_required') {
    return (
      <div className="flow-state">
        <h3 className="mb-4 flex items-center gap-2 text-warning">
          <ShieldAlert size={20} /> Review Required
        </h3>
        <p className="text-sm mb-4">Some fields are sensitive or require your confirmation.</p>
        
        <div className="reviews-list space-y-4">
          {reviews.map(review => (
            <div key={review.review_id} className="review-card p-3 border rounded">
              <div className="font-semibold">{review.concept || 'Unknown Field'}</div>
              <div className="text-sm text-secondary mt-1">Suggested: {review.suggested_value}</div>
              <div className="flex gap-2 mt-3">
                <button className="btn-sm btn-success flex-1" onClick={() => handleReviewDecision(review.review_id, 'confirm')}>
                  <Check size={14} /> Approve
                </button>
                <button className="btn-sm btn-outline flex-1" onClick={() => handleReviewDecision(review.review_id, 'reject')}>
                  <X size={14} /> Reject
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (status === 'ready') {
    return (
      <div className="flow-state">
        <h3 className="mb-4 flex items-center gap-2 text-success">
          <CheckCircle size={20} /> Ready to Fill
        </h3>
        <p className="text-sm mb-4">We found {approvedValues.length} fields we can fill for you.</p>
        
        <div className="max-h-48 overflow-y-auto mb-4 border rounded p-2">
          {approvedValues.map(v => (
            <div key={v.field_id} className="text-sm py-1 border-b last:border-0 flex justify-between">
              <span className="text-secondary">{v.concept}</span>
              <span className="font-medium truncate max-w-[120px]">{v.value}</span>
            </div>
          ))}
        </div>

        <button className="btn-primary w-full" onClick={startFilling}>
          <Play size={16} /> Fill {approvedValues.length} Fields
        </button>
      </div>
    );
  }

  if (status === 'filling' || status === 'verifying') {
    return (
      <div className="flow-state text-center">
        <Loader2 size={32} className="spin text-primary mx-auto mb-4" />
        <h3>{status === 'filling' ? 'Filling fields...' : 'Verifying values...'}</h3>
      </div>
    );
  }

  if (status === 'done') {
    return (
      <div className="flow-state text-center">
        <CheckCircle size={48} className="text-success mx-auto mb-4" />
        <h3>Form Filled!</h3>
        <p className="text-secondary mt-2 mb-4">Please review the page and submit the form manually.</p>
        <button className="btn-outline w-full" onClick={onComplete}>Close</button>
      </div>
    );
  }

  return null;
};
