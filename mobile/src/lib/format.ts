/** ₹ amount with Indian digit grouping (12,34,567.50). Whole rupees drop the paise. */
export function rupees(value: number): string {
  const fixed = Math.abs(value).toFixed(2);
  const [whole, paise] = fixed.split('.');
  const last3 = whole.slice(-3);
  const rest = whole.slice(0, -3);
  const grouped = rest ? rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',') + ',' + last3 : last3;
  const sign = value < 0 ? '-' : '';
  return `${sign}₹${grouped}${paise === '00' ? '' : '.' + paise}`;
}

export function percentOff(mrp: number, selling: number): number {
  if (!mrp || selling >= mrp) return 0;
  return Math.round(((mrp - selling) / mrp) * 100);
}

/** "2026-10-23 16:15:16" (server UTC) -> "23 Oct, 9:45 pm" in the phone's timezone. */
export function shortDateTime(serverTimestamp: string): string {
  const d = new Date(serverTimestamp.replace(' ', 'T') + 'Z');
  if (Number.isNaN(d.getTime())) return serverTimestamp;
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const h = d.getHours();
  const m = d.getMinutes().toString().padStart(2, '0');
  return `${d.getDate()} ${months[d.getMonth()]}, ${h % 12 || 12}:${m} ${h < 12 ? 'am' : 'pm'}`;
}
