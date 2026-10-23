import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { CartBar } from '@/components/CartBar';
import { ProductImage } from '@/components/ProductImage';
import { QtyStepper } from '@/components/QtyStepper';
import { imageUrl, PurchasedItem } from '@/lib/api';
import { rupees, shortDateTime } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { usePurchasedItems } from '@/lib/usePurchasedItems';
import { useAuth } from '@/state/auth';
import { lineKey, useCart } from '@/state/cart';

/** Everything this customer has bought before, most to least, with one-tap reorder. */
export default function RegularsScreen() {
  const auth = useAuth();
  const { items, error, reload } = usePurchasedItems();
  const [refreshing, setRefreshing] = useState(false);

  if (items === null && !error) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.brand} size="large" />
      </View>
    );
  }

  return (
    <View style={{ flex: 1 }}>
      <FlatList
        data={items ?? []}
        keyExtractor={(i) => String(i.id)}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            tintColor={colors.brand}
            onRefresh={async () => {
              setRefreshing(true);
              await reload();
              setRefreshing(false);
            }}
          />
        }
        ListHeaderComponent={
          error ? (
            <Text style={styles.error}>{error}</Text>
          ) : (
            <Text style={styles.caption}>Ranked by how much you've bought, across all your orders.</Text>
          )
        }
        ListEmptyComponent={
          error ? undefined : (
            <View style={styles.center}>
              <Ionicons name="repeat" size={48} color={colors.inkFaint} />
              <Text style={styles.emptyTitle}>No orders yet</Text>
              <Text style={styles.emptyText}>Items you order will show up here, most bought first.</Text>
            </View>
          )
        }
        renderItem={({ item, index }) => <RegularRow item={item} rank={index + 1} apiUrl={auth.apiUrl} />}
      />
      <CartBar label="View cart" onPress={() => router.navigate('/cart')} />
    </View>
  );
}

function RegularRow({ item, rank, apiUrl }: { item: PurchasedItem; rank: number; apiUrl: string }) {
  const cart = useCart();
  const qty = cart.qtyOf(item.id, 'PCS');
  const caseQty = cart.qtyOf(item.id, 'CASE');
  const pieces = Number.isInteger(item.total_qty) ? item.total_qty : item.total_qty.toFixed(1);

  return (
    <View style={styles.row}>
      <Text style={styles.rank}>{rank}</Text>
      <ProductImage uri={imageUrl(apiUrl, item.image_url)} name={item.name} category={item.category} size={56} />
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={styles.name} numberOfLines={2}>
          {item.name}
        </Text>
        <Text style={styles.meta} numberOfLines={1}>
          {[item.size, item.brand].filter(Boolean).join(' · ')}
        </Text>
        <Text style={styles.stats} numberOfLines={1}>
          {pieces} pcs · {item.times_ordered} order{item.times_ordered === 1 ? '' : 's'} · last {shortDateTime(item.last_ordered_at).split(',')[0]}
        </Text>
        {item.case_selling_price !== null && (
          <Pressable onPress={() => cart.add(item, 'CASE')} hitSlop={6} accessibilityRole="button">
            <Text style={styles.caseLink}>
              {caseQty > 0 ? `${caseQty} case${caseQty === 1 ? '' : 's'} in cart · ` : ''}+ Case of {item.case_size}
            </Text>
          </Pressable>
        )}
      </View>
      <View style={{ alignItems: 'flex-end', gap: 6 }}>
        {item.selling_price > 0 ? (
          <Text style={styles.price}>{rupees(item.selling_price)}</Text>
        ) : (
          <Text style={styles.onRequest}>On request</Text>
        )}
        <QtyStepper
          compact
          qty={qty}
          onAdd={() => cart.add(item, 'PCS')}
          onChange={(n) => cart.setQty(lineKey(item.id, 'PCS'), n)}
        />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  list: { padding: 12, gap: 10, paddingBottom: 100, flexGrow: 1 },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 8 },
  caption: { fontSize: 12, color: colors.inkMuted, marginBottom: 2 },
  error: { color: colors.danger, fontWeight: '700', textAlign: 'center' },
  emptyTitle: { fontSize: 17, fontWeight: '800', color: colors.ink },
  emptyText: { fontSize: 13, color: colors.inkMuted, textAlign: 'center' },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 12,
    ...shadow,
  },
  rank: { width: 22, textAlign: 'center', fontSize: 15, fontWeight: '900', color: colors.inkFaint },
  name: { fontSize: 14, fontWeight: '700', color: colors.ink },
  meta: { fontSize: 11, color: colors.inkMuted },
  stats: { fontSize: 11, color: colors.green, fontWeight: '700' },
  caseLink: { fontSize: 11, color: colors.brand, fontWeight: '800', marginTop: 2 },
  price: { fontSize: 14, fontWeight: '800', color: colors.ink },
  onRequest: { fontSize: 11, fontWeight: '700', color: colors.amber },
});
