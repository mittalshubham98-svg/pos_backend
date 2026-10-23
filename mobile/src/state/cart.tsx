import { createContext, ReactNode, useContext, useMemo, useReducer, useState } from 'react';

import type { CatalogItem, OrderPayload, Uom } from '@/lib/api';

/** One cart line per item *and* unit: the same item can sit in the cart both loose and by
 *  the case, since the two are priced differently. */
export type CartLine = { key: string; item: CatalogItem; uom: Uom; qty: number };

type Action =
  | { type: 'add'; item: CatalogItem; uom: Uom }
  | { type: 'setQty'; key: string; qty: number }
  | { type: 'clear' };

export const lineKey = (itemId: number, uom: Uom) => `${itemId}:${uom}`;

function reducer(lines: CartLine[], action: Action): CartLine[] {
  switch (action.type) {
    case 'add': {
      const key = lineKey(action.item.id, action.uom);
      const existing = lines.find((l) => l.key === key);
      if (existing) return lines.map((l) => (l.key === key ? { ...l, qty: l.qty + 1 } : l));
      return [...lines, { key, item: action.item, uom: action.uom, qty: 1 }];
    }
    case 'setQty':
      return action.qty <= 0
        ? lines.filter((l) => l.key !== action.key)
        : lines.map((l) => (l.key === action.key ? { ...l, qty: action.qty } : l));
    case 'clear':
      return [];
  }
}

export function piecesFor(line: CartLine): number {
  return line.uom === 'CASE' ? line.qty * line.item.case_size : line.qty;
}

/** Client-side estimate from catalogue prices; the server's tax engine computes the bill. */
export function lineTotal(line: CartLine): number {
  const perPiece = line.uom === 'CASE' ? (line.item.case_selling_price ?? line.item.selling_price) : line.item.selling_price;
  return perPiece * piecesFor(line);
}

type CartState = {
  lines: CartLine[];
  itemCount: number;
  total: number;
  mrpTotal: number;
  qtyOf: (itemId: number, uom: Uom) => number;
  add: (item: CatalogItem, uom?: Uom) => void;
  setQty: (key: string, qty: number) => void;
  /** Free-text "items not in the list", sent with the order as unlisted_text. */
  unlisted: string;
  setUnlisted: (text: string) => void;
  /** Something to order: catalogue lines and/or an unlisted request. */
  hasAnything: boolean;
  clear: () => void;
  toOrderLines: () => OrderPayload['lines'];
};

const CartContext = createContext<CartState | null>(null);

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, dispatch] = useReducer(reducer, []);
  const [unlisted, setUnlisted] = useState('');

  const value = useMemo<CartState>(() => {
    const total = lines.reduce((sum, l) => sum + lineTotal(l), 0);
    const mrpTotal = lines.reduce((sum, l) => sum + (l.item.mrp || 0) * piecesFor(l), 0);
    return {
      lines,
      itemCount: lines.reduce((n, l) => n + l.qty, 0),
      total,
      // Items without an MRP would otherwise show a fake "saving".
      mrpTotal: Math.max(mrpTotal, total),
      qtyOf: (itemId, uom) => lines.find((l) => l.key === lineKey(itemId, uom))?.qty ?? 0,
      add: (item, uom = 'PCS') => dispatch({ type: 'add', item, uom }),
      setQty: (key, qty) => dispatch({ type: 'setQty', key, qty }),
      unlisted,
      setUnlisted,
      hasAnything: lines.length > 0 || unlisted.trim().length > 0,
      clear: () => {
        dispatch({ type: 'clear' });
        setUnlisted('');
      },
      toOrderLines: () => lines.map((l) => ({ item_id: l.item.id, qty: l.qty, uom: l.uom })),
    };
  }, [lines, unlisted]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartState {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error('useCart must be used inside <CartProvider>');
  return ctx;
}
