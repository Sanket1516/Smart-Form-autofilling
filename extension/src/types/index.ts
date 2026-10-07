export interface FieldOption {
  /** Unique identifier for this radio, checkbox, or select option. */
  option_id: string;
  id?: string;
  name?: string;
  value: string;
  label: string;
  checked: boolean;
  selected?: boolean;
  disabled?: boolean;
  /** Stable path to the individual option control, when it has one. */
  dom_path?: string;
}

export interface FieldObject {
  field_id: string;
  /** HTML tag name; `tag` is kept for the existing API contract. */
  tag: string;
  input_type: string;
  /** Legacy alias consumed by existing popup code. */
  type?: string;
  name?: string;
  id?: string;
  placeholder?: string;
  label?: string;
  associated_label?: string;
  aria_label?: string;
  aria_labelledby?: string;
  aria_labelledby_text?: string;
  aria_description?: string;
  autocomplete?: string;
  required: boolean;
  pattern?: string;
  nearby_text?: string;
  current_value: string;
  checked: boolean | null;
  options: FieldOption[];
  option_labels: string[];
  option_values: string[];
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
