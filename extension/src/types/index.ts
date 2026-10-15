/** Description of one form control sent to the backend. Never contains the control's value. */
export interface FieldOption {
  option_id: string;
  value: string;
  label: string;
  disabled?: boolean;
}

export interface FieldObject {
  field_id: string;
  tag: string;
  input_type: string;
  label: string;
  question?: string;
  name?: string;
  id?: string;
  placeholder?: string;
  aria_label?: string;
  aria_description?: string;
  autocomplete?: string;
  pattern?: string;
  section?: string;
  nearby_text?: string;
  required: boolean;
  has_value: boolean;
  max_length?: number;
  options: FieldOption[];
}

/** A file-upload control. Describes the control only; never any file contents. */
export interface UploadField {
  field_id: string;
  label: string;
  name?: string;
  id?: string;
  placeholder?: string;
  accept?: string;
  multiple: boolean;
  required: boolean;
  section?: string;
  nearby_text?: string;
  /** Short helper text next to the control (size limits, formats, instructions). */
  instructions?: string;
  has_file: boolean;
}

export interface PageInfo {
  origin: string;
  url: string;
  title: string;
  /** First top-level heading, used only to recognise the application (e.g. an exam). */
  heading?: string;
}

export interface ExtractResponse {
  fields: FieldObject[];
  uploads: UploadField[];
  skipped: number;
  page: PageInfo;
}

/** A document in the user's library, as returned by GET /documents. */
export interface DocumentRecord {
  document_id: string;
  file_name: string;
  file_type: string;
  file_size: number;
  document_type: string | null;
  document_type_confidence: number | null;
  status: string;
  uploaded_at: string;
  fact_count: number;
}

export interface AttachResult {
  field_id: string;
  attached: boolean;
  verified: boolean;
  reason?: string;
}

export interface SelectedOption {
  label: string;
  value: string;
}

export interface RecommendationSource {
  type: 'profile' | 'document' | 'memory' | 'user' | 'derived';
  document_id?: string | null;
  document_name?: string | null;
  page?: number | null;
  snippet?: string | null;
}

export interface RecommendationCandidate {
  value: unknown;
  confidence: number;
  source?: RecommendationSource | null;
}

export type RecommendationStatus =
  | 'ready'
  | 'needs_review'
  | 'missing_information'
  | 'security_blocked'
  | 'skipped'
  | 'error'
  | 'approved'
  | 'edited'
  | 'rejected';

export interface Recommendation {
  recommendation_id: string;
  field_id: string;
  field_label: string;
  input_type: string;
  required: boolean;
  concept: string | null;
  recommended_value: unknown;
  confidence: number;
  status: RecommendationStatus;
  reason: string;
  requires_confirmation: boolean;
  origin?: string | null;
  source?: RecommendationSource | null;
  candidates: RecommendationCandidate[];
  options: SelectedOption[];
  selected_option?: SelectedOption | null;
}

export interface ApprovedValue {
  field_id: string;
  value: string;
  input_type: string;
  field_label?: string;
  selected_option?: SelectedOption | null;
  /** The user explicitly agreed to replace a value already present on the page. */
  overwrite?: boolean;
}

export interface FillResult {
  field_id: string;
  applied: boolean;
  verified: boolean;
  reason?: string;
}

export type ContentRequest =
  | { type: 'SFA_PING' }
  | { type: 'SFA_EXTRACT' }
  | { type: 'SFA_FILL'; values: ApprovedValue[] }
  | { type: 'SFA_ATTACH_FILE'; field_id: string; file_name: string; mime: string; data_base64: string; replace?: boolean };

/** Sent by the content script (debounced) when controls were added or removed. */
export interface FormChangedMessage {
  type: 'SFA_FORM_CHANGED';
}
