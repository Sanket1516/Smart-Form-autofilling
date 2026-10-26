/* Landing-page copy and the sample record used by every demonstration on the page.
 * Everything here is fictional demonstration data: no real person, document or identifier.
 * The page never calls the API; the real product lives behind /login. */

export const SAMPLE = {
  name: 'Asha R. Verma',
  dob: '14 / 08 / 2004',
  dobIso: '2004-08-14',
  dobAlt: '14 / 08 / 2005',
  gender: 'Female',
  father: 'Rakesh Verma',
  addressLine1: '21 Lakeview Road, Kothrud',
  addressLine2: 'Pune, Maharashtra 411038',
  phone: '+91 90000 12345',
  phoneNormalized: '+919000012345',
  email: 'asha.verma@example.com',
  applicantId: 'SF 4821 7730 0915',
  applicantIdMasked: '•••• •••• 0915',
  class10: '91.40%',
  class12: '88.20%',
} as const;

/** A field on the sample document: where its value sits (canvas px on the 1024x1448 sheet)
 * and how it reads before and after extraction. */
export interface SampleField {
  key: string;
  label: string;
  raw: string;
  concept: string;
  value: string;
  /** As printed on the sheet. */
  printed: string;
  rect: [x: number, y: number, w: number, h: number];
}

export const DOC_SIZE = { w: 1024, h: 1448 } as const;

export const FIELDS: SampleField[] = [
  { key: 'name', label: 'Full name', raw: 'Full Name : Asha R. Verma', concept: 'full_name', value: SAMPLE.name, printed: SAMPLE.name, rect: [66, 262, 430, 46] },
  { key: 'dob', label: 'Date of birth', raw: 'Date of Birth  14 / 08 / 2004', concept: 'date_of_birth', value: SAMPLE.dobIso, printed: SAMPLE.dob, rect: [66, 362, 280, 46] },
  { key: 'address', label: 'Address', raw: 'Address 21 Lakeview Rd, Kothrud…', concept: 'address', value: 'Pune 411038', printed: SAMPLE.addressLine1, rect: [66, 562, 560, 86] },
  { key: 'phone', label: 'Phone', raw: 'Phone No. +91 90000 12345', concept: 'phone', value: SAMPLE.phoneNormalized, printed: SAMPLE.phone, rect: [66, 702, 330, 46] },
  { key: 'email', label: 'Email', raw: 'E-mail asha.verma@example.com', concept: 'email', value: SAMPLE.email, printed: SAMPLE.email, rect: [516, 702, 440, 46] },
  { key: 'id', label: 'Applicant ID', raw: 'Applicant ID SF 4821 7730 0915', concept: 'applicant_id', value: SAMPLE.applicantIdMasked, printed: SAMPLE.applicantId, rect: [66, 802, 400, 46] },
];

/** Story chapters bound to the 3D stage, as fractions of the story's scroll length. */
export const CHAPTERS = [
  { id: 'hero', from: 0, to: 0.13 },
  { id: 'upload', from: 0.13, to: 0.29 },
  { id: 'scan', from: 0.29, to: 0.49 },
  { id: 'core', from: 0.49, to: 0.67 },
  { id: 'record', from: 0.67, to: 0.83 },
  { id: 'browser', from: 0.83, to: 1 },
] as const;

export type ChapterId = (typeof CHAPTERS)[number]['id'];

export const PIPELINE = [
  { n: '01', title: 'Extracted text', body: 'Native PDF text and tables, or OCR output for scans and photos.' },
  { n: '02', title: 'Identify', body: 'Labels, values and tables are located with page-level evidence.' },
  { n: '03', title: 'Context', body: 'The document type decides which rules apply to which lines.' },
  { n: '04', title: 'Classify', body: 'Each value is mapped to one of ~150 canonical concepts and validated.' },
  { n: '05', title: 'Structured output', body: 'Sourced facts you can confirm, edit or reject.' },
] as const;

export const NAV_LINKS = [
  { href: '#top', label: 'Home' },
  { href: '#how', label: 'How it works' },
  { href: '#features', label: 'Features' },
  { href: '#extension', label: 'Browser extension' },
  { href: '#security', label: 'Security' },
  { href: '#faq', label: 'FAQ' },
] as const;

export const FAQ = [
  {
    q: 'Does Smart Form submit forms for me?',
    a: 'No. The extension fills only the fields you tick, reads each one back from the page to confirm it held, and stops. Submitting is always your action.',
  },
  {
    q: 'Which documents can I upload?',
    a: 'PDF, DOCX, TXT and PNG/JPG images. Native PDF text and tables are read directly; scanned pages and photos go through OCR with deskew, contrast and orientation correction.',
  },
  {
    q: 'What happens when two documents disagree?',
    a: 'Both values are kept with their sources and the field is marked as a conflict. You choose the correct value once in your profile, and forms use your choice from then on.',
  },
  {
    q: 'Is an AI model required?',
    a: 'No. Extraction starts with deterministic rules, label matching and checksum validation. A language model is optional and only fills the gaps those rules leave; its output is schema-checked before use.',
  },
  {
    q: 'Which fields will it never fill?',
    a: 'Passwords, one-time codes and payment fields are blocked. Declarations and consent boxes are left for you to tick yourself, and sensitive identifiers always need your explicit choice.',
  },
  {
    q: 'Which browsers does the extension support?',
    a: 'It is a Chrome Manifest V3 extension, so it runs in Chrome and Chromium-based browsers. It reads a page only after you open it on that tab.',
  },
] as const;
