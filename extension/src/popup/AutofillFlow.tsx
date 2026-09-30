import { useState, useEffect } from 'react';
import { Loader2, CheckCircle, Play, Check, X, ShieldAlert, Save } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000/api/v1';

/** Always reads token fresh from storage to avoid stale React state. */
function getToken(): Promise<string> {
  return new Promise((resolve) => {
    chrome.storage.local.get(['token'], (res) => resolve(res.token || ''));
  });
}

function questionFor(label: string): string {
  const normalized = label.trim().replace(/\*+$/, '').trim();
  const lower = normalized.toLowerCase();
  if (/about yourself|about me|experience|describe|achievement|project|career goal/.test(lower)) {
    return normalized.endsWith('?') ? normalized : `${normalized}?`;
  }
  if (/\b(full|applicant|candidate|legal) name\b/.test(lower) || (lower.includes('name') && /applicant|candidate/.test(lower))) return 'What is your full name?';
  if (/\b(date of birth|birth date|birthdate|dob)\b/.test(lower)) return 'What is your date of birth?';
  if (/\b(address|residence)\b/.test(lower)) return `What is your ${lower.includes('permanent') ? 'permanent ' : ''}address?`;
  if (/\b(annual|yearly|family)? ?income\b/.test(lower)) return 'What is your annual income?';
  if (/\b(email)\b/.test(lower)) return 'What is your email address?';
  if (/\b(phone|mobile|telephone)\b/.test(lower)) return 'What is your phone number?';
  return `What is your ${normalized.toLowerCase()}?`;
}

export const AutofillFlow = ({ 
  sessionId, 
  onComplete
}: { 
  sessionId: string, 
  token: string,  // kept for prop compat but we read fresh from storage
  onComplete: () => void 
}) => {
  const [status, setStatus] = useState<'processing' | 'review_required' | 'information_required' | 'ready' | 'filling' | 'verifying' | 'done'>('processing');
  const [reviews, setReviews] = useState<any[]>([]);
  const [approvedValues, setApprovedValues] = useState<any[]>([]);
  const [missingFields, setMissingFields] = useState<any[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [saveForFuture, setSaveForFuture] = useState<Record<string, boolean>>({});
  const [answerError, setAnswerError] = useState<string | null>(null);
  const [savingAnswers, setSavingAnswers] = useState(false);
  const [reviewSaveChoices, setReviewSaveChoices] = useState<Record<string, boolean>>({});
  const [editingApprovedValues, setEditingApprovedValues] = useState(false);

  // Poll for session status
  useEffect(() => {
    if (status !== 'processing') return;

    const interval = setInterval(async () => {
      try {
        const freshToken = await getToken();
        const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${freshToken}` }
        });
        const data = await res.json();

        if (data.data.status === 'review_required') {
          setStatus('review_required');
          fetchReviews();
          clearInterval(interval);
        } else if (data.data.status === 'information_required') {
          setStatus('information_required');
          fetchMissingFields();
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

  const fetchMissingFields = async () => {
    try {
      const freshToken = await getToken();
      const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}/recommendations`, {
        headers: { 'Authorization': `Bearer ${freshToken}` }
      });
      const data = await res.json();
      const recommendations = data.data?.recommendations || [];
      const required = recommendations.filter((item: any) => item.required && item.status === 'missing_information');
      setMissingFields(required);
      if (required.length === 0) {
        const sessionRes = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}`, {
          headers: { 'Authorization': `Bearer ${freshToken}` }
        });
        const sessionData = await sessionRes.json();
        if (sessionData.data?.status === 'review_required') {
          setStatus('review_required');
          fetchReviews();
        } else {
          setStatus('ready');
          fetchApprovedValues();
        }
      }
    } catch (err) {
      console.error(err);
    }
  };

  const submitAnswers = async () => {
    const pending = missingFields.map((field) => ({
      field_id: field.field_id,
      value: answers[field.field_id]?.trim() || '',
      save_for_future: Boolean(saveForFuture[field.field_id]),
    }));
    if (pending.some((answer) => !answer.value)) return;
    setSavingAnswers(true);
    setAnswerError(null);
    try {
      const freshToken = await getToken();
      const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}/answers`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${freshToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ answers: pending })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error?.message || data?.detail || 'Could not save answers');
      const nextStatus = data.data.status;
      if (nextStatus === 'information_required') {
        setStatus('information_required');
        await fetchMissingFields();
      } else if (nextStatus === 'review_required') {
        setStatus('review_required');
        fetchReviews();
      } else {
        setStatus('ready');
        fetchApprovedValues();
      }
    } catch (err) {
      setAnswerError(err instanceof Error ? err.message : 'Could not save answers');
    } finally {
      setSavingAnswers(false);
    }
  };

  const fetchReviews = async () => {
    try {
      const freshToken = await getToken();
      const res = await fetch(`${API_BASE_URL}/reviews/pending`, {
        headers: { 'Authorization': `Bearer ${freshToken}` }
      });
      const data = await res.json();
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
      const freshToken = await getToken();
      const res = await fetch(`${API_BASE_URL}/forms/sessions/${sessionId}/approved-values`, {
        headers: { 'Authorization': `Bearer ${freshToken}` }
      });
      const data = await res.json();
      setApprovedValues(data.data.approved_values || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleReviewDecision = async (reviewId: string, decision: 'confirm' | 'reject', value?: string) => {
    try {
      const freshToken = await getToken();
      await fetch(`${API_BASE_URL}/reviews/${reviewId}/decision`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${freshToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ decision, value, save_for_future: Boolean(reviewSaveChoices[reviewId]) })
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

  const startFilling = async () => {
    setStatus('filling');
    const freshToken = await getToken();

    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0] && tabs[0].id) {
        chrome.tabs.sendMessage(tabs[0].id, {
          type: 'FILL_FIELDS',
          payload: { approvedValues, sessionId, token: freshToken }
        }, () => {
          // After content script confirms receipt, wait briefly then show done
          setTimeout(() => setStatus('done'), 1500);
        });
      } else {
        setStatus('done');
      }
    });
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
              <label className="save-choice mt-2">
                <input
                  type="checkbox"
                  checked={Boolean(reviewSaveChoices[review.review_id])}
                  onChange={(event) => setReviewSaveChoices((current) => ({ ...current, [review.review_id]: event.target.checked }))}
                />
                <Save size={14} /> Save this information for future forms
              </label>
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

  if (status === 'information_required') {
    const allAnswered = missingFields.length > 0 && missingFields.every((field) => answers[field.field_id]?.trim());
    return (
      <div className="flow-state">
        <h3 className="mb-2">Let’s fill this form</h3>
        <p className="text-sm text-secondary mb-4">I need {missingFields.length} required {missingFields.length === 1 ? 'answer' : 'answers'} that aren’t in your approved information.</p>
        <div className="ask-me-list">
          {missingFields.map((field, index) => {
            const isNarrative = /textarea|about|experience|describe|achievement|project|goal/i.test(`${field.input_type} ${field.field_label}`);
            return (
              <div key={field.field_id} className="ask-me-field">
                <label className="font-semibold" htmlFor={`answer-${field.field_id}`}>
                  {index + 1}/{missingFields.length} · {questionFor(field.field_label || field.concept || 'this field')}
                </label>
                {isNarrative ? (
                  <textarea
                    id={`answer-${field.field_id}`}
                    rows={4}
                    value={answers[field.field_id] || ''}
                    onChange={(event) => setAnswers((current) => ({ ...current, [field.field_id]: event.target.value }))}
                    placeholder="Enter your answer"
                  />
                ) : (
                  <input
                    id={`answer-${field.field_id}`}
                    type={field.input_type === 'date' ? 'date' : 'text'}
                    value={answers[field.field_id] || ''}
                    onChange={(event) => setAnswers((current) => ({ ...current, [field.field_id]: event.target.value }))}
                    placeholder={`Your ${String(field.field_label || 'answer').toLowerCase()}`}
                  />
                )}
                <label className="save-choice">
                  <input
                    type="checkbox"
                    checked={Boolean(saveForFuture[field.field_id])}
                    onChange={(event) => setSaveForFuture((current) => ({ ...current, [field.field_id]: event.target.checked }))}
                  />
                  <Save size={14} /> Save this answer for future forms
                </label>
              </div>
            );
          })}
        </div>
        {answerError && <p className="answer-error">{answerError}</p>}
        <button className="btn-primary w-full" onClick={submitAnswers} disabled={!allAnswered || savingAnswers}>
          {savingAnswers ? <Loader2 size={16} className="spin" /> : null} Continue to review
        </button>
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
            <div key={v.field_id} className="text-sm py-2 border-b last:border-0">
              {editingApprovedValues ? (
                <label className="review-edit-field">
                  <span className="text-secondary">{v.field_label || v.concept}</span>
                  {/textarea|experience|narrative|description|about/i.test(`${v.input_type} ${v.concept} ${v.field_label}`) ? (
                    <textarea
                      rows={3}
                      value={String(v.value ?? '')}
                      onChange={(event) => setApprovedValues((values) => values.map((item) =>
                        item.field_id === v.field_id ? { ...item, value: event.target.value } : item
                      ))}
                    />
                  ) : (
                    <input
                      type={v.input_type === 'date' ? 'date' : 'text'}
                      value={String(v.value ?? '')}
                      onChange={(event) => setApprovedValues((values) => values.map((item) =>
                        item.field_id === v.field_id ? { ...item, value: event.target.value } : item
                      ))}
                    />
                  )}
                </label>
              ) : (
                <div className="flex justify-between">
                  <span className="text-secondary">{v.field_label || v.concept}</span>
                  <span className="font-medium truncate max-w-[120px]">{v.value}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {editingApprovedValues ? (
          <button className="btn-outline w-full" onClick={() => setEditingApprovedValues(false)}>Done reviewing</button>
        ) : (
          <button className="btn-outline w-full" onClick={() => setEditingApprovedValues(true)}>Review / Edit</button>
        )}
        <button className="btn-primary w-full" onClick={startFilling} disabled={editingApprovedValues || approvedValues.length === 0}>
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
