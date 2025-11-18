export function computeStarFills(rating = 0, totalStars = 5) {
  const safeRating = Math.max(0, Math.min(totalStars, Number.isFinite(rating) ? rating : 0));
  const fills = [];
  for (let i = 0; i < totalStars; i += 1) {
    const remaining = safeRating - i;
    const percent = remaining >= 1 ? 100 : remaining > 0 ? Math.round(remaining * 100) : 0;
    fills.push(percent);
  }
  return fills;
}
