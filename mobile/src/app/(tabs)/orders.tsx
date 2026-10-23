import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { api, Order } from '@/lib/api';
import { rupees, shortDateTime } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';

export default function OrdersScreen() {
  const auth = useAuth();
  const [orders, setOrders] = useState<Order[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    if (!auth.session) return;
    try {
      setError(null);
      setOrders(await api.myOrders(auth.apiUrl, auth.session.token));
    } catch (err) {
      auth.handleAuthError(err);
      setError(err instanceof Error ? err.message : 'Could not load your orders');
    }
  }, [auth]);

  // Refetch each time the tab is opened, so a just-placed order shows up.
  useFocusEffect(
    useCallback(() => {
      load();
    }, [load]),
  );

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>My orders</Text>
      </View>
      {orders === null && !error ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brand} size="large" />
        </View>
      ) : (
        <FlatList
          data={orders ?? []}
          keyExtractor={(o) => String(o.id)}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              tintColor={colors.brand}
              onRefresh={async () => {
                setRefreshing(true);
                await load();
                setRefreshing(false);
              }}
            />
          }
          ListHeaderComponent={error ? <Text style={styles.error}>{error}</Text> : undefined}
          ListEmptyComponent={
            error ? undefined : (
              <View style={styles.center}>
                <Ionicons name="receipt-outline" size={52} color={colors.inkFaint} />
                <Text style={styles.emptyTitle}>No orders yet</Text>
                <Text style={styles.emptyText}>Orders you place will show up here.</Text>
              </View>
            )
          }
          renderItem={({ item }) => <OrderCard order={item} />}
        />
      )}
    </SafeAreaView>
  );
}

function OrderCard({ order }: { order: Order }) {
  const billed = order.status === 'BILLED';
  const preview = order.lines
    .slice(0, 3)
    .map((l) => l.name)
    .join(', ');
  const more = order.lines.length - 3;
  return (
    <View style={styles.card}>
      <View style={styles.cardTop}>
        <View>
          <Text style={styles.po}>{order.po_number}</Text>
          <Text style={styles.date}>{shortDateTime(order.created_at)}</Text>
        </View>
        <View style={[styles.badge, billed ? styles.badgeBilled : styles.badgeOpen]}>
          <Text style={[styles.badgeText, { color: billed ? colors.green : colors.amber }]}>
            {billed ? 'Billed' : 'Received'}
          </Text>
        </View>
      </View>
      {preview ? (
        <Text style={styles.lines} numberOfLines={2}>
          {preview}
          {more > 0 ? ` +${more} more` : ''}
        </Text>
      ) : null}
      {order.unlisted_text ? (
        <Text style={styles.unlisted} numberOfLines={2}>
          Unlisted: {order.unlisted_text}
        </Text>
      ) : null}
      <View style={styles.cardBottom}>
        <Text style={styles.payment}>
          {order.utr ? `UPI · ${order.utr}` : 'On account'}
          {order.invoice_number ? ` · ${order.invoice_number}` : ''}
        </Text>
        <Text style={styles.total}>{rupees(order.totals.grand_total)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingVertical: 12, backgroundColor: colors.card },
  title: { fontSize: 20, fontWeight: '900', color: colors.ink },
  list: { padding: 12, gap: 10, flexGrow: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 },
  emptyTitle: { fontSize: 17, fontWeight: '800', color: colors.ink },
  emptyText: { fontSize: 13, color: colors.inkMuted },
  error: { color: colors.danger, fontWeight: '700', textAlign: 'center', marginBottom: 8 },
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: 14, gap: 8, ...shadow },
  cardTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start' },
  po: { fontSize: 15, fontWeight: '800', color: colors.ink },
  date: { marginTop: 2, fontSize: 12, color: colors.inkMuted },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeBilled: { backgroundColor: colors.greenTint },
  badgeOpen: { backgroundColor: colors.amberTint },
  badgeText: { fontSize: 11, fontWeight: '800' },
  lines: { fontSize: 13, color: colors.ink },
  unlisted: { fontSize: 12, color: colors.inkMuted, fontStyle: 'italic' },
  cardBottom: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
    paddingTop: 8,
  },
  payment: { flexShrink: 1, fontSize: 12, color: colors.inkMuted },
  total: { fontSize: 16, fontWeight: '900', color: colors.ink },
});
