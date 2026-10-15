/**
 * Typed client for the Smart Form backend.
 *
 * Every response uses the `{ success, data, message }` / `{ success: false, error }`
 * envelope. Errors become `ApiError` with the server's message; a 401 also
 * emits `auth:expired` so the app can sign the user out in one place.
 */

export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
const API = `${API_BASE_URL}/api/v1`;
const TOKEN_KEY = 'token';

export class ApiError extends Error {
  constructor(message: string, readonly status: number, readonly code: string) {
    super(message);
  }
}

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

interface Options {
  method?: string;
  body?: unknown;
  form?: FormData;
  auth?: boolean;
}

async function raw(path: string, { method = 'GET', body, form, auth = true }: Options = {}): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  let response: Response;
  try {
    response = await fetch(`${API}${path}`, {
      method,
      headers,
      body: form ?? (body === undefined ? undefined : JSON.stringify(body)),
    });
  } catch {
    throw new ApiError('Cannot reach the server. Check that the backend is running.', 0, 'NETWORK_ERROR');
  }
  if (!response.ok) {
    let code = `HTTP_${response.status}`;
    let message = `Request failed (${response.status})`;
    try {
      const payload = await response.json();
      code = payload?.error?.code ?? code;
      message = payload?.error?.message ?? message;
      const fields = payload?.error?.details?.fields as Array<{ loc: string[]; msg: string }> | undefined;
      if (code === 'VALIDATION_ERROR' && fields?.length) {
        message = fields.map((f) => `${f.loc.slice(1).join('.')}: ${f.msg}`).join('; ');
      }
    } catch {
      // keep the generic message
    }
    if (response.status === 401 && auth) {
      tokenStore.clear();
      window.dispatchEvent(new Event('auth:expired'));
    }
    throw new ApiError(message, response.status, code);
  }
  return response;
}

async function request<T>(path: string, options: Options = {}): Promise<T> {
  const response = await raw(path, options);
  const payload = await response.json();
  return payload.data as T;
}

// ---------------------------------------------------------------------------- types

export interface User {
  user_id: string;
  full_name: string;
  email: string;
  status?: string;
}

export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'failed' | 'requires_review' | 'deleted';

export interface DocumentData {
  document_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  document_type?: string | null;
  document_type_confidence?: number | null;
  status: DocumentStatus;
  current_stage?: string | null;
  progress: number;
  processing_error?: string | null;
  warnings: string[];
  uploaded_at: string;
  processed_at?: string | null;
  page_count?: number | null;
  fact_count: number;
  index_status: 'pending' | 'indexed' | 'failed' | 'empty';
  chunk_count: number;
  index_error?: string | null;
}

export interface Fact {
  fact_id: string;
  concept: string;
  value: unknown;
  raw_value?: unknown;
  value_type: string;
  origin: string;
  status: string;
  source_document_id: string;
  document_name?: string | null;
  source_page?: number | null;
  evidence_text?: string | null;
  extraction_method?: string | null;
  confidence: number;
  is_user_confirmed: boolean;
  created_at: string;
  updated_at: string;
}

export interface FactSource {
  fact_id: string;
  document_id: string;
  document_name?: string | null;
  page?: number | null;
  evidence?: string | null;
  origin: string;
  confidence: number;
  is_user_confirmed: boolean;
}

export interface ConflictCandidate {
  value: unknown;
  confidence: number;
  is_user_confirmed: boolean;
  document_id: string;
  document_name?: string | null;
  page?: number | null;
  evidence?: string | null;
  sources: FactSource[];
}

export interface Conflict {
  id: string;
  concept: string;
  label: string;
  conflict_type: 'CROSS_DOCUMENT' | 'INTRA_DOCUMENT' | 'VERIFIED_VS_NEW';
  candidates: ConflictCandidate[];
}

export interface ProfileField {
  concept: string;
  label: string;
  status: 'resolved' | 'conflict' | 'multiple';
  value: unknown;
  values: unknown[];
  confidence: number;
  is_user_confirmed: boolean;
  origin: string;
  sensitive: boolean;
  group?: string;
  data_type?: string;
  sources: FactSource[];
}

export interface Profile {
  user_id: string;
  sections: Record<string, Record<string, unknown>>;
  fields: ProfileField[];
  groups?: Array<{ key: string; label: string }>;
}

export type RequirementStatus = 'available' | 'needs_confirmation' | 'conflict' | 'missing' | 'needs_user_input';

export interface ExamRequirement {
  concept: string;
  label: string;
  required: boolean;
  sensitive: boolean;
  status: RequirementStatus;
  value?: unknown;
  candidates?: unknown[];
  sources: string[];
  reason?: string;
  missing_subjects?: string[];
  evidence: Array<{ document_type: string; label: string }>;
}

export interface ExamUpload {
  id: string;
  label: string;
  required: boolean | null;
  reason?: string | null;
  formats: string[];
  min_kb?: number | null;
  max_kb?: number | null;
  verified: boolean;
  note?: string | null;
}

export interface ExamReadiness {
  exam_id: string;
  name: string;
  last_reviewed?: string;
  verified_against_official_bulletin: boolean;
  note?: string;
  summary: Partial<Record<RequirementStatus, number>>;
  sections: Array<{ title: string; requirements: ExamRequirement[] }>;
  uploads: ExamUpload[];
}

export interface ExamSummary {
  exam_id: string;
  name: string;
  conducting_body?: string;
  official_site?: string;
  last_reviewed?: string;
  verified_against_official_bulletin: boolean;
  note?: string;
}

export interface UploadCheck {
  upload_id: string;
  file_name: string;
  size_kb: number;
  dimensions?: { width: number; height: number } | null;
  ok: boolean;
  problems: string[];
  verified_rules: boolean;
  note?: string | null;
}

export interface Concept {
  concept: string;
  description: string;
  data_type: string;
  sensitive: boolean;
  single_valued: boolean;
}

export interface Memory {
  memory_id: string;
  label: string;
  concept: string;
  value: string;
  indexed: boolean;
  updated_at?: string;
}

export interface DiscoveredFact {
  id: string;
  source_document_id: string;
  source_page?: number | null;
  field: string;
  semantic_type: string;
  value: unknown;
  raw_value?: unknown;
  original_label?: string | null;
  confidence: number;
  evidence_text: string;
  ontology?: string | null;
  origin: string;
  extraction_method: string;
  document_type?: string | null;
  masked?: boolean;
}

export interface Review {
  review_id: string;
  session_id: string;
  field_id: string;
  field_label: string;
  concept?: string | null;
  suggested_value: unknown;
  confidence: number;
  reason: string;
  requires_confirmation: boolean;
  source?: { type: string; document_name?: string | null; page?: number | null; snippet?: string | null } | null;
  candidates: Array<{ value: unknown; confidence: number; source?: { document_name?: string | null } | null }>;
}

export interface FormSession {
  session_id: string;
  website_origin: string;
  page_url: string;
  form_id: string;
  status: string;
  started_at?: string | null;
  total_fields: number;
  filled_fields: number;
  reviewed_fields: number;
  failed_fields: number;
  counts: Record<string, number>;
}

export interface Correction {
  correction_id: string;
  concept: string;
  original_value: unknown;
  corrected_value: unknown;
  reason: string;
  created_at: string;
}

export type RagAnswerStatus = 'answered' | 'partial' | 'insufficient_evidence' | 'no_documents' | 'documents_not_ready';

export interface RagAnswerFact {
  fact_id: string;
  concept: string;
  label: string;
  value: unknown;
  status: 'verified' | 'extracted' | 'needs_review';
  document_id?: string | null;
  document_name?: string | null;
  document_type?: string | null;
  page?: number | null;
  evidence?: string | null;
  confidence: number;
}

export interface RagAnswer {
  answer: string;
  status: RagAnswerStatus;
  confidence: number;
  question_type: string;
  /** structured: built from stored facts by code; generated: written by the AI from cited evidence;
   * evidence_only: the AI was unavailable, so only evidence is shown. */
  answer_mode: 'structured' | 'generated' | 'evidence_only' | 'none';
  sources: Array<{ chunk_id: string; document_id: string; document_name: string; document_type?: string; page_number: number; similarity: number; snippet: string }>;
  facts: RagAnswerFact[];
  derived: Array<{ label: string; value: string; method: string; inputs: string[] }>;
  inferences: string[];
  missing: Array<{ concept: string; label: string; reason: string; suggested_documents: string[] }>;
  conflicts: Array<{ concept: string; label: string; values: Array<{ value: unknown; document_name?: string | null; page?: number | null }> }>;
  requirements: Array<{ label: string; outcome: 'met' | 'not_met' | 'unknown' | 'needs_confirmation' | 'info'; detail: string; source: string }>;
  documents: Array<{ document_id: string; document_name: string; document_type?: string | null; status: string; searched: boolean }>;
  warnings: string[];
}

export interface AskOptions {
  documentIds?: string[];
  history?: Array<{ role: 'user' | 'assistant'; content: string }>;
  examId?: string;
}

export interface ServiceHealth {
  api: string;
  mongodb: string;
  chromadb: string;
  llm: string;
  embedding_service: string;
  details: Record<string, string>;
}

// ---------------------------------------------------------------------------- endpoints

export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: User }>('/auth/login', { method: 'POST', body: { email, password }, auth: false }),
  register: (full_name: string, email: string, password: string, confirm_password: string) =>
    request<User>('/auth/register', { method: 'POST', body: { full_name, email, password, confirm_password }, auth: false }),
  me: () => request<User>('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),
  deleteAccount: () => request('/auth/me', { method: 'DELETE' }),
};

export const documentApi = {
  list: () => request<{ documents: DocumentData[]; total: number }>('/documents?limit=100'),
  get: (id: string) => request<DocumentData>(`/documents/${id}`),
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<DocumentData>('/documents', { method: 'POST', form });
  },
  reprocess: (id: string) => request(`/documents/${id}/reprocess`, { method: 'POST' }),
  remove: (id: string) => request(`/documents/${id}`, { method: 'DELETE' }),
  facts: (id: string) => request<{ facts: Fact[] }>(`/documents/${id}/facts`).then((d) => d.facts),
  /** Fetch the file with the Authorization header and return an object URL (caller revokes it). */
  blobUrl: async (id: string, kind: 'preview' | 'download') => {
    const response = await raw(`/documents/${id}/${kind}`);
    return URL.createObjectURL(await response.blob());
  },
};

export const factsApi = {
  list: () => request<{ facts: Fact[] }>('/profile/facts').then((d) => d.facts),
  add: (concept: string, value: string) => request<Fact>('/profile/facts', { method: 'POST', body: { concept, value } }),
  update: (id: string, value: unknown) =>
    request<Fact>(`/profile/facts/${id}`, { method: 'PUT', body: { value, is_user_confirmed: true } }),
  remove: (id: string) => request(`/profile/facts/${id}`, { method: 'DELETE' }),
  conflicts: () => request<Conflict[]>('/profile/facts/conflicts'),
  resolve: (concept: string, body: { resolution: 'candidate' | 'custom' | 'reject'; candidate_index?: number; custom_value?: string }) =>
    request(`/profile/facts/conflicts/${encodeURIComponent(concept)}/resolve`, { method: 'PATCH', body }),
  discovered: (documentId?: string) =>
    request<DiscoveredFact[]>(`/profile/discovered-facts${documentId ? `?document_id=${encodeURIComponent(documentId)}` : ''}`),
};

export const profileApi = {
  get: () => request<Profile>('/profile'),
  concepts: () => request<Concept[]>('/profile/concepts'),
  memories: () => request<{ memories: Memory[] }>('/profile/memories').then((d) => d.memories),
  removeMemory: (id: string) => request(`/profile/memories/${id}`, { method: 'DELETE' }),
  corrections: () => request<{ corrections: Correction[] }>('/profile/corrections').then((d) => d.corrections),
  deleteAllData: () => request('/profile/data', { method: 'DELETE' }),
};

export const reviewsApi = {
  pending: () => request<{ reviews: Review[] }>('/reviews/pending').then((d) => d.reviews),
  decide: (id: string, decision: 'confirm' | 'edit' | 'reject' | 'skip', value?: string, saveForFuture = false) =>
    request(`/reviews/${id}/decision`, { method: 'POST', body: { decision, value, save_for_future: saveForFuture } }),
};

export const formsApi = {
  sessions: () => request<{ sessions: FormSession[] }>('/forms/sessions').then((d) => d.sessions),
};

export const ragApi = {
  ask: (question: string, options: AskOptions = {}) =>
    request<RagAnswer>('/retrieval/rag/answer', {
      method: 'POST',
      body: {
        question,
        ...(options.documentIds && options.documentIds.length ? { document_ids: options.documentIds } : {}),
        ...(options.history && options.history.length ? { history: options.history.slice(-12) } : {}),
        ...(options.examId ? { exam_id: options.examId } : {}),
      },
    }),
};

export const examsApi = {
  list: () => request<ExamSummary[]>('/exams'),
  readiness: (examId: string) => request<ExamReadiness>(`/exams/${encodeURIComponent(examId)}/readiness`),
  checkUpload: (examId: string, uploadId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return request<UploadCheck>(
      `/exams/${encodeURIComponent(examId)}/uploads/${encodeURIComponent(uploadId)}/check`,
      { method: 'POST', form },
    );
  },
};

const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  AADHAAR_CARD: 'Aadhaar card', PAN_CARD: 'PAN card', VOTER_ID: 'Voter ID', DRIVING_LICENCE: 'Driving licence',
  PASSPORT: 'Passport', CLASS_10_MARKSHEET: 'Class 10 marksheet', CLASS_12_MARKSHEET: 'Class 12 marksheet',
  BIRTH_CERTIFICATE: 'Birth certificate', BANK_PASSBOOK: 'Bank passbook', BANK_STATEMENT: 'Bank statement',
  ELECTRICITY_BILL: 'Electricity bill', RATION_CARD: 'Ration card', INCOME_CERTIFICATE: 'Income certificate',
  CASTE_CERTIFICATE: 'Caste certificate', CASTE_VALIDITY_CERTIFICATE: 'Caste validity certificate',
  NON_CREAMY_LAYER_CERTIFICATE: 'Non-creamy layer certificate', DOMICILE_CERTIFICATE: 'Domicile certificate',
};

export function documentTypeLabel(type: string): string {
  return DOCUMENT_TYPE_LABELS[type] ?? type.replace(/_/g, ' ').toLowerCase().replace(/^\w/, (c) => c.toUpperCase());
}

/** Rows of a record table (subjects, transactions, household members). */
export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export const healthApi = {
  services: () => request<ServiceHealth>('/health/services', { auth: false }),
};

export function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.map(formatValue).join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

export function conceptLabel(concept: string): string {
  const [, key = concept] = concept.split('.', 2);
  const text = key.replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}
