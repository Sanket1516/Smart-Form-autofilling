/** Client-side checks that mirror the backend's upload rules. */

export const ACCEPTED = '.pdf,.docx,.txt,.png,.jpg,.jpeg';
const ACCEPTED_EXTENSIONS = ACCEPTED.split(',');
export const MAX_MB = 10;

export function validateFile(file: File): string | null {
  const name = file.name.toLowerCase();
  if (!ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
    return 'Unsupported file type. Upload a PDF, DOCX, TXT, PNG or JPG file.';
  }
  if (file.size === 0) return 'The file is empty.';
  if (file.size > MAX_MB * 1024 * 1024) return `The file is larger than ${MAX_MB} MB.`;
  return null;
}
