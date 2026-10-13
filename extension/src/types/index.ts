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

export interface PageInfo {
  origin: string;
  url: string;
  title: string;
}

export interface ExtractResponse {
  fields: FieldObject[];
  skipped: number;
  page: PageInfo;
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
  | { type: 'SFA_FILL'; values: ApprovedValue[] };
