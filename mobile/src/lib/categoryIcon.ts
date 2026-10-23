import { ALL, DEALS } from '@/lib/catalog';

/** Keyword → emoji, checked in order; first match wins. Keywords are matched against the
 *  lower-cased category name, so CSV spellings like "STAPELS AND GRAINS" still hit "grain". */
const RULES: [string[], string][] = [
  [['dry fruit', 'nut', 'kaju', 'badam'], '🥜'],
  [['spice', 'masala', 'condiment'], '🌶️'],
  [['salt', 'sugar', 'jaggery'], '🧂'],
  [['flour', 'atta', 'grain', 'staple', 'rice', 'dal', 'pulse'], '🌾'],
  [['oil', 'ghee'], '🫙'],
  [['dairy', 'milk', 'paneer', 'butter'], '🥛'],
  [['beverage', 'drink', 'tea', 'coffee', 'juice'], '🥤'],
  [['chocolate', 'confection', 'candy', 'sweet'], '🍫'],
  [['snack', 'namkeen', 'chips', 'biscuit'], '🍿'],
  [['instant', 'noodle', 'ready'], '🍜'],
  [['sauce', 'spread', 'ketchup', 'jam'], '🍅'],
  [['pickle', 'achar'], '🥒'],
  [['murabba', 'honey'], '🍯'],
  [['personal', 'soap', 'shampoo', 'care'], '🧴'],
  [['clean', 'detergent', 'home and'], '🧽'],
  [['disposable', 'plate', 'cup'], '🥡'],
  [['kitchen', 'utensil'], '🍳'],
  [['household', 'utilit'], '🏠'],
  [['light', 'bulb', 'electric'], '💡'],
  [['vegetable', 'fruit'], '🥬'],
];

export function categoryIcon(category: string | null | undefined): string {
  if (category === ALL) return '🛒';
  if (category === DEALS) return '🏷️';
  const name = (category ?? '').toLowerCase();
  for (const [keywords, emoji] of RULES) if (keywords.some((k) => name.includes(k))) return emoji;
  return '🛍️';
}
