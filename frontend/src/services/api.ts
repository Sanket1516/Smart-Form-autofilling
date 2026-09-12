export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const getBaseUrl = () => API_BASE_URL;

export async function getHealth() {
  const response = await fetch(`${API_BASE_URL}/api/v1/health`);
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body?.data?.status ?? "Backend health check failed");
  }
  return body.data;
}

const getHeaders = (isFormData = false) => {
  const token = localStorage.getItem('token');
  const headers: HeadersInit = {};
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  if (!isFormData) {
    headers['Content-Type'] = 'application/json';
  }
  
  return headers;
};

export interface DocumentResponse {
  document_id: string;
  file_name: string;
  document_type: string;
  status: string;
  uploaded_at: string;
  processed_at?: string;
  page_count?: number;
}

export const documentApi = {
  getDocuments: async (): Promise<DocumentResponse[]> => {
    const res = await fetch(`${getBaseUrl()}/api/v1/documents`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch documents');
    const json = await res.json();
    return json.data.documents || [];
  },

  getDocument: async (id: string): Promise<DocumentResponse> => {
    const res = await fetch(`${getBaseUrl()}/api/v1/documents/${id}`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch document');
    const json = await res.json();
    return json.data;
  },

  uploadDocument: async (file: File): Promise<DocumentResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    
    const res = await fetch(`${getBaseUrl()}/api/v1/documents`, {
      method: 'POST',
      headers: getHeaders(true),
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload document');
    const json = await res.json();
    return json.data;
  },

  processDocument: async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/v1/documents/${id}/process`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to process document');
  },

  deleteDocument: async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/v1/documents/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete document');
  },
  
  getDocumentStatus: async (id: string): Promise<{status: string; current_stage: string; progress: number; error: string | null}> => {
    const res = await fetch(`${getBaseUrl()}/api/v1/documents/${id}/status`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch document status');
    const json = await res.json();
    return json.data;
  }
};

export const profileApi = {
  getProfile: async () => {
    const res = await fetch(`${getBaseUrl()}/api/v1/profile/me`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch profile');
    const json = await res.json();
    return json.data;
  },
  updateProfile: async (data: any) => {
    const res = await fetch(`${getBaseUrl()}/api/v1/profile/me`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to update profile');
    const json = await res.json();
    return json.data;
  }
};

export const factsApi = {
  getFacts: async (concept?: string) => {
    const url = concept ? `${getBaseUrl()}/api/v1/facts?concept=${concept}` : `${getBaseUrl()}/api/v1/facts`;
    const res = await fetch(url, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch facts');
    const json = await res.json();
    return json.data.facts || [];
  },
  deleteFact: async (id: string) => {
    const res = await fetch(`${getBaseUrl()}/api/v1/facts/${id}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete fact');
  }
};

export const reviewsApi = {
  getPendingReviews: async () => {
    const res = await fetch(`${getBaseUrl()}/api/v1/reviews/pending`, { headers: getHeaders() });
    if (!res.ok) throw new Error('Failed to fetch pending reviews');
    const json = await res.json();
    return json.data.reviews || [];
  },
  submitDecision: async (id: string, decision: string, value?: string) => {
    const res = await fetch(`${getBaseUrl()}/api/v1/reviews/${id}/decision`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify({ decision, value }),
    });
    if (!res.ok) throw new Error('Failed to submit review decision');
    const json = await res.json();
    return json.data;
  }
};
