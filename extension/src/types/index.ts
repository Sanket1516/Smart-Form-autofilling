export interface FieldObject {
  field_id: string;
  tag?: string;
  type?: string;
  name?: string;
  id?: string;
  placeholder?: string;
  label?: string;
  aria_label?: string;
  aria_description?: string;
  autocomplete?: string;
  required: boolean;
  pattern?: string;
  nearby_text?: string;
  section_context?: string;
  position?: Record<string, any>;
  dom_context: Record<string, any>;
  accessibility_context: Record<string, any>;
  visual_context?: Record<string, any>;
  concept?: string;
}

export type AuthState = 'not-signed-in' | 'connected' | 'session-expired';

export interface ExtensionState {
  authState: AuthState;
  token?: string;
}
