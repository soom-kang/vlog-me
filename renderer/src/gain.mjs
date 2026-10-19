/** @param {number} frame @param {number[][]} points */
export function gainAt(frame, points) {
  if (frame <= points[0][0]) return 10 ** (points[0][1] / 20);
  for (let i = 1; i < points.length; i++) {
    if (frame <= points[i][0]) {
      const [left, right] = [points[i - 1], points[i]];
      const db = left[1] + ((frame - left[0]) / (right[0] - left[0])) * (right[1] - left[1]);
      return 10 ** (db / 20);
    }
  }
  return 10 ** (points[points.length - 1][1] / 20);
}
