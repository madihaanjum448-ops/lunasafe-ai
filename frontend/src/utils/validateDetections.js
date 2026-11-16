/**
 * Strict check of a detections list. Returns an error message string,
 * or null when the list is valid.
 * bbox = [x1, y1, x2, y2] in original-image pixels.
 */
export function validateDetections(list, imageMeta) {
  if (!Array.isArray(list)) {
    return 'Expected an array of detections (or an object with a "detections" array).';
  }
  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const w = Number(imageMeta?.width);
  const h = Number(imageMeta?.height);
  const sizeKnown = Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0;

  for (let i = 0; i < list.length; i += 1) {
    const d = list[i];
    const n = i + 1;
    if (!d || typeof d !== 'object') return `Detection ${n}: not an object.`;
    if (d.id === undefined || d.id === null) return `Detection ${n}: missing id.`;
    if (!Array.isArray(d.bbox) || d.bbox.length !== 4 || !d.bbox.every(isNum)) {
      return `Detection ${n}: bbox must be 4 numbers [x1, y1, x2, y2].`;
    }
    const [x1, y1, x2, y2] = d.bbox;
    if (x1 >= x2 || y1 >= y2) return `Detection ${n}: bbox needs x1 < x2 and y1 < y2.`;
    if (!isNum(d.confidence) || d.confidence < 0 || d.confidence > 1) {
      return `Detection ${n}: confidence must be a number from 0 to 1.`;
    }
    if (sizeKnown && (x1 < 0 || y1 < 0 || x2 > w || y2 > h)) {
      return `Detection ${n}: bbox lies outside the image (${w}x${h}).`;
    }
    if (d.polygon !== undefined && d.polygon !== null) {
      const ok =
        Array.isArray(d.polygon) &&
        d.polygon.length >= 3 &&
        d.polygon.every((p) => Array.isArray(p) && p.length === 2 && p.every(isNum));
      if (!ok) return `Detection ${n}: polygon must be 3 or more [x, y] points.`;
    }
  }
  return null;
}
