/**
 * Image upload validation constants and limits for LunaSafe AI
 */

// Upload Limits
export const MAX_FILE_SIZE_MB = 50;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const MAX_IMAGE_WIDTH = 8192;
export const MAX_IMAGE_HEIGHT = 8192;
export const MAX_IMAGE_DIMENSION = 8192;

// Allowed file types (PNG, JPEG, TIFF, WEBP)
export const ALLOWED_IMAGE_EXTENSIONS = ['png', 'jpg', 'jpeg', 'tiff', 'tif', 'webp'];

export const ALLOWED_IMAGE_MIME_TYPES = [
  'image/png',
  'image/jpeg',
  'image/pjpeg',
  'image/webp',
  'image/tiff',
  'image/x-tiff',
];

export const ACCEPTED_FILE_TYPES_STRING =
  'image/png,image/jpeg,image/webp,image/tiff,.png,.jpg,.jpeg,.webp,.tif,.tiff';

// Standard Validation Error Messages
export const UPLOAD_ERROR_MESSAGES = {
  INVALID_TYPE: 'Only PNG, JPEG, TIFF or WEBP images are allowed.',
  FILE_TOO_LARGE: `File is too large. Maximum size is ${MAX_FILE_SIZE_MB} MB.`,
  EMPTY_FILE: 'This file is empty.',
  CORRUPT_IMAGE: 'This image is corrupted and cannot be opened.',
  IMAGE_TOO_LARGE: `Image is too large. Maximum resolution is ${MAX_IMAGE_WIDTH} x ${MAX_IMAGE_HEIGHT} px.`,
};

// Information notes
export const MULTIPLE_FILES_NOTE =
  'Multiple files selected. Only the first file was used.';

/**
 * Validates whether a file is an allowed image type (PNG, JPEG, TIFF, or WEBP).
 * Checks both extension and MIME type.
 *
 * @param {File} file
 * @returns {boolean}
 */
export function isValidFileType(file) {
  if (!file || !file.name) return false;

  const ext = file.name.includes('.')
    ? file.name.split('.').pop().toLowerCase()
    : '';
  const isAllowedExt = ext ? ALLOWED_IMAGE_EXTENSIONS.includes(ext) : false;

  const mime = file.type ? file.type.toLowerCase() : '';
  const isAllowedMime = mime ? ALLOWED_IMAGE_MIME_TYPES.includes(mime) : false;

  // Reject if file extension is present but not in allowed extensions
  if (ext && !isAllowedExt) {
    return false;
  }

  // Reject if MIME type is present and not an allowed image MIME (and not generic binary)
  if (mime && !isAllowedMime && mime !== 'application/octet-stream') {
    return false;
  }

  // Must match either allowed extension or allowed MIME type
  return isAllowedExt || isAllowedMime;
}
