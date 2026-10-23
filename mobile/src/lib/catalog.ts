import type { CatalogItem } from '@/lib/api';
import { percentOff } from '@/lib/format';

/** Pseudo-categories shown alongside the real ones in the catalogue. */
export const ALL = 'All items';
export const DEALS = 'Top deals';

export const isDeal = (i: CatalogItem) => i.on_offer || percentOff(i.mrp, i.selling_price) > 0;

/** Store promotions first, then biggest discount off MRP. */
export const byBestDeal = (a: CatalogItem, b: CatalogItem) =>
  Number(b.on_offer) - Number(a.on_offer) || percentOff(b.mrp, b.selling_price) - percentOff(a.mrp, a.selling_price);

/** Catalogue categories arrive in CAPS from the CSV import; show them as Title Case. */
export function titleCase(s: string): string {
  if (s === ALL || s === DEALS) return s;
  return s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}
