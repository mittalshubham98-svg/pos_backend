import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';

import { api, PurchasedItem } from '@/lib/api';
import { useAuth } from '@/state/auth';

/** The signed-in customer's previously bought items (most to least), refetched whenever the
 *  screen comes into focus so a just-placed order is reflected straight away. */
export function usePurchasedItems() {
  const auth = useAuth();
  const [items, setItems] = useState<PurchasedItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!auth.session) return;
    try {
      setError(null);
      setItems(await api.purchasedItems(auth.apiUrl, auth.session.token));
    } catch (err) {
      auth.handleAuthError(err);
      setError(err instanceof Error ? err.message : 'Could not load your items');
    }
  }, [auth]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  return { items, error, reload: load };
}
