/**
 * Fields the extension never decides on the user's behalf.
 *  - declaration: legal statements, consent and undertakings; the user must tick them personally.
 *  - sensitive: identity numbers, bank details, category/eligibility claims; never pre-selected,
 *    filled only when the user ticks them.
 */
export type Guard = 'declaration' | 'sensitive' | null;

const DECLARATION = /\b(i declare|declaration|i agree|agree(s)? to|consent|terms|undertaking|i certify|hereby|true and correct|i accept|i confirm)\b/i;
const SENSITIVE = /aadh?aa?r|\bpan\b|passport|\baccount\b|\bifsc\b|\bmicr\b|\bbank\b|categor|caste|religion|disab|pwbd|\bpwd\b|income|\bews\b|\bobc\b|\bncl\b|creamy|domicile|tribe|minority|\bsc\b|\bst\b/i;

export function guardFor(label: string, concept: string | null | undefined, inputType: string): Guard {
  if ((inputType === 'checkbox' || inputType === 'radio') && DECLARATION.test(label)) return 'declaration';
  if (inputType === 'checkbox' && /\b(i|we) /i.test(label) && /(agree|accept|declare|certify|confirm)/i.test(label)) return 'declaration';
  return SENSITIVE.test(`${label} ${concept ?? ''}`) ? 'sensitive' : null;
}
