import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { FlatList, Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { CartBar } from '@/components/CartBar';
import { ProductImage } from '@/components/ProductImage';
import { QtyStepper } from '@/components/QtyStepper';
import { UnlistedBox } from '@/components/UnlistedBox';
import { imageUrl } from '@/lib/api';
import { rupees } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';
import { CartLine, lineTotal, piecesFor, useCart } from '@/state/cart';

export default function CartScreen() {
  const cart = useCart();
  const auth = useAuth();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Your cart</Text>
        {cart.hasAnything && (
          <Pressable onPress={cart.clear} hitSlop={10}>
            <Text style={styles.clear}>Clear</Text>
          </Pressable>
        )}
      </View>

      <FlatList
        data={cart.lines}
        keyExtractor={(l) => l.key}
        contentContainerStyle={styles.list}
        keyboardShouldPersistTaps="handled"
        automaticallyAdjustKeyboardInsets
        ListEmptyComponent={
          <View style={styles.empty}>
            <Ionicons name="basket-outline" size={56} color={colors.inkFaint} />
            <Text style={styles.emptyTitle}>No catalogue items yet</Text>
            <Text style={styles.emptyText}>Add items from the catalogue, or write what you need in the box below.</Text>
            <Pressable onPress={() => router.navigate('/catalogue')} style={styles.primary}>
              <Text style={styles.primaryText}>Browse catalogue</Text>
            </Pressable>
          </View>
        }
        renderItem={({ item }) => <CartRow line={item} apiUrl={auth.apiUrl} />}
        ListFooterComponent={
          <View style={{ gap: 10, marginTop: 6 }}>
            {cart.lines.length > 0 && <BillSummary />}
            <UnlistedBox title="Items not in the list" />
          </View>
        }
      />

      <CartBar label="Checkout" onPress={() => router.push('/checkout')} />
    </SafeAreaView>
  );
}

function CartRow({ line, apiUrl }: { line: CartLine; apiUrl: string }) {
  const cart = useCart();
  const { item } = line;
  const unit = line.uom === 'CASE' ? `Case of ${item.case_size} · ${rupees(item.case_selling_price ?? item.selling_price)}/pc` : rupees(item.selling_price);
  return (
    <View style={styles.row}>
      <ProductImage uri={imageUrl(apiUrl, item.image_url)} name={item.name} category={item.category} size={56} />
      <View style={{ flex: 1 }}>
        <Text style={styles.rowName} numberOfLines={2}>
          {item.name}
        </Text>
        <Text style={styles.rowMeta} numberOfLines={1}>
          {[item.size, unit].filter(Boolean).join(' · ')}
        </Text>
        {line.uom === 'CASE' && <Text style={styles.rowPieces}>{piecesFor(line)} pcs</Text>}
      </View>
      <View style={{ alignItems: 'flex-end', gap: 6 }}>
        <QtyStepper compact qty={line.qty} onAdd={() => cart.add(item, line.uom)} onChange={(n) => cart.setQty(line.key, n)} />
        <Text style={styles.rowTotal}>{rupees(lineTotal(line))}</Text>
      </View>
    </View>
  );
}

function BillSummary() {
  const cart = useCart();
  const saving = cart.mrpTotal - cart.total;
  return (
    <View style={styles.bill}>
      <Text style={styles.billTitle}>Bill details</Text>
      <Row label="Items total (MRP)" value={rupees(cart.mrpTotal)} />
      {saving >= 1 && <Row label="You save" value={`− ${rupees(saving)}`} green />}
      <View style={styles.divider} />
      <Row label="Estimated total" value={rupees(Math.round(cart.total))} bold />
      <Text style={styles.note}>
        Prices include GST. The store confirms final quantities and rates on your tax invoice.
      </Text>
    </View>
  );
}

function Row({ label, value, bold, green }: { label: string; value: string; bold?: boolean; green?: boolean }) {
  return (
    <View style={styles.billRow}>
      <Text style={[styles.billLabel, bold && styles.billBold]}>{label}</Text>
      <Text style={[styles.billValue, bold && styles.billBold, green && { color: colors.green }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: colors.card,
  },
  title: { fontSize: 20, fontWeight: '900', color: colors.ink },
  clear: { color: colors.brand, fontWeight: '700' },
  list: { padding: 12, gap: 10, paddingBottom: 100, flexGrow: 1 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 12,
    ...shadow,
  },
  rowName: { fontSize: 14, fontWeight: '700', color: colors.ink },
  rowMeta: { marginTop: 2, fontSize: 12, color: colors.inkMuted },
  rowPieces: { marginTop: 2, fontSize: 11, color: colors.green, fontWeight: '700' },
  rowTotal: { fontSize: 14, fontWeight: '800', color: colors.ink },
  bill: { marginTop: 6, backgroundColor: colors.card, borderRadius: radius.md, padding: 16, gap: 8, ...shadow },
  billTitle: { fontSize: 15, fontWeight: '800', color: colors.ink, marginBottom: 2 },
  billRow: { flexDirection: 'row', justifyContent: 'space-between' },
  billLabel: { fontSize: 13, color: colors.inkMuted },
  billValue: { fontSize: 13, color: colors.ink, fontWeight: '600' },
  billBold: { fontSize: 15, fontWeight: '900', color: colors.ink },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.line, marginVertical: 4 },
  note: { fontSize: 11, color: colors.inkFaint, marginTop: 4 },
  empty: { alignItems: 'center', justifyContent: 'center', padding: 24, gap: 10 },
  emptyTitle: { fontSize: 18, fontWeight: '800', color: colors.ink },
  emptyText: { fontSize: 13, color: colors.inkMuted, textAlign: 'center' },
  primary: { marginTop: 8, backgroundColor: colors.brand, borderRadius: radius.sm, paddingHorizontal: 20, paddingVertical: 12 },
  primaryText: { color: '#fff', fontWeight: '800' },
});
