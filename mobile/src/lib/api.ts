import Constants from 'expo-constants';

/** Server address baked in at build time (app.json -> extra.apiUrl). The login screen can
 *  override it, so one APK works against the shop PC on Wi-Fi or a hosted domain later. */
export const DEFAULT_API_URL: string =
  (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? 'http://192.168.29.75:8000';

export type CatalogItem = {
  id: number;
  name: string;
  brand: string | null;
  size: string | null;
  category: string | null;
  mrp: number;
  selling_price: number;
  promo_status: string;
  discount_rate: number;
  on_offer: boolean;
  image_url: string | null;
  case_size: number;
  case_selling_price: number | null;
};

/** categories and brands are derived server-side from the live catalogue. */
export type Catalog = { categories: string[]; brands: string[]; items: CatalogItem[] };

/** A catalogue item this customer has ordered before, with how much of it they've bought. */
export type PurchasedItem = CatalogItem & {
  total_qty: number; // pieces, across all their orders
  times_ordered: number;
  last_ordered_at: string;
};

/** A home-screen banner uploaded in the admin portal. link: "" | "deals" | "catalogue" | "category:<name>". */
export type Banner = { id: number; image_url: string; title: string; link: string };

export type AuthResult = {
  token: string;
  role: string;
  expires_in_minutes: number;
  cust_code: string;
  name: string | null;
};

export type Uom = 'PCS' | 'CASE';

export type OrderPayload = {
  lines: { item_id: number; qty: number; uom: Uom }[];
  unlisted_text: string;
  utr: string | null;
};

export type Order = {
  id: number;
  po_number: string;
  status: 'PO_RECEIVED' | 'BILLED' | string;
  utr: string | null;
  unlisted_text: string;
  created_at: string;
  invoice_number: string | null;
  lines: { id: number; name: string; qty: number; uom: string; case_size: number; selling: number }[];
  totals: { taxable: number; cgst: number; sgst: number; selling_raw: number; grand_total: number; round_off: number };
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export function normaliseBaseUrl(raw: string): string {
  let url = raw.trim().replace(/\/+$/, '');
  if (url && !/^https?:\/\//i.test(url)) url = 'http://' + url;
  return url;
}

/** FastAPI errors come back as {detail: string} or {detail: [{msg}, ...]}. */
function detailMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
  }
  return fallback;
}

async function request<T>(
  baseUrl: string,
  path: string,
  { method = 'GET', token, body }: { method?: string; token?: string | null; body?: unknown } = {},
): Promise<T> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers['Content-Type'] = 'application/json';

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 20000);
  let res: Response;
  try {
    res = await fetch(baseUrl + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    throw new ApiError(0, `Can't reach the store server at ${baseUrl}. Check your internet / Wi-Fi.`);
  } finally {
    clearTimeout(timer);
  }

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!res.ok) throw new ApiError(res.status, detailMessage(data, `Server error ${res.status}`));
  return data as T;
}

export const api = {
  login: (baseUrl: string, custCode: string, password: string) =>
    request<AuthResult>(baseUrl, '/api/auth', { method: 'POST', body: { cust_code: custCode, password } }),

  catalog: (baseUrl: string) => request<Catalog>(baseUrl, '/api/catalog'),

  banners: (baseUrl: string) => request<Banner[]>(baseUrl, '/api/banners'),

  placeOrder: (baseUrl: string, token: string, payload: OrderPayload) =>
    request<Order>(baseUrl, '/api/orders', { method: 'POST', token, body: payload }),

  myOrders: (baseUrl: string, token: string) => request<Order[]>(baseUrl, '/api/customer/orders', { token }),

  purchasedItems: (baseUrl: string, token: string) =>
    request<PurchasedItem[]>(baseUrl, '/api/customer/purchased-items', { token }),
};

export const upiQrUrl = (baseUrl: string) => `${baseUrl}/static/images/upi_qr.png`;
export const imageUrl = (baseUrl: string, path: string | null) => (path ? baseUrl + path : null);
