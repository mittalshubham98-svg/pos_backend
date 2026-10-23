import { memo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ProductImage } from '@/components/ProductImage';
import { QtyStepper } from '@/components/QtyStepper';
import { CatalogItem, imageUrl } from '@/lib/api';
import { percentOff, rupees } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { lineKey, useCart } from '@/state/cart';

type Props = { item: CatalogItem; apiUrl: string; width: number };

function ProductCardBase({ item, apiUrl, width }: Props) {
  const cart = useCart();
  const qty = cart.qtyOf(item.id, 'PCS');
  const caseQty = cart.qtyOf(item.id, 'CASE');
  const off = percentOff(item.mrp, item.selling_price);
  const imageSize = width - 24;

  return (
    <View style={[styles.card, { width }]}>
      <View>
        <ProductImage uri={imageUrl(apiUrl, item.image_url)} name={item.name} size={imageSize} />
        {off > 0 && (
          <View style={styles.offBadge}>
            <Text style={styles.offText}>{off}%</Text>
            <Text style={styles.offText}>OFF</Text>
          </View>
        )}
      </View>

      {item.promo_status ? (
        <Text style={styles.promo} numberOfLines={1}>
          {item.promo_status}
        </Text>
      ) : null}
      <Text style={styles.name} numberOfLines={2}>
        {item.name}
      </Text>
      <Text style={styles.meta} numberOfLines={1}>
        {[item.size, item.brand].filter(Boolean).join(' · ')}
      </Text>

      <View style={styles.footer}>
        <View style={{ flexShrink: 1 }}>
          <Text style={styles.price}>{rupees(item.selling_price)}</Text>
          {item.mrp > item.selling_price && <Text style={styles.mrp}>{rupees(item.mrp)}</Text>}
        </View>
        <QtyStepper
          compact
          qty={qty}
          onAdd={() => cart.add(item, 'PCS')}
          onChange={(n) => cart.setQty(lineKey(item.id, 'PCS'), n)}
        />
      </View>

      {item.case_selling_price !== null && (
        <Pressable
          onPress={() => cart.add(item, 'CASE')}
          style={({ pressed }) => [styles.caseRow, pressed && { opacity: 0.7 }]}
          accessibilityRole="button"
          accessibilityLabel={`Add a case of ${item.case_size}`}
        >
          <Text style={styles.caseText} numberOfLines={1}>
            Case of {item.case_size} · {rupees(item.case_selling_price)}/pc
          </Text>
          <Text style={styles.caseAdd}>{caseQty > 0 ? `${caseQty} in cart` : '+ Case'}</Text>
        </Pressable>
      )}
    </View>
  );
}

export const ProductCard = memo(ProductCardBase);

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.md, padding: 12, ...shadow },
  offBadge: {
    position: 'absolute',
    top: 0,
    left: 0,
    backgroundColor: '#2563EB',
    borderTopLeftRadius: 10,
    borderBottomRightRadius: 10,
    paddingHorizontal: 6,
    paddingVertical: 3,
    alignItems: 'center',
  },
  offText: { color: '#fff', fontSize: 9, fontWeight: '900', lineHeight: 11 },
  promo: {
    marginTop: 8,
    alignSelf: 'flex-start',
    backgroundColor: colors.amberTint,
    color: colors.amber,
    fontSize: 10,
    fontWeight: '800',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    overflow: 'hidden',
  },
  name: { marginTop: 8, fontSize: 13, fontWeight: '700', color: colors.ink, minHeight: 34, lineHeight: 17 },
  meta: { marginTop: 2, fontSize: 11, color: colors.inkMuted },
  footer: { marginTop: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 6 },
  price: { fontSize: 14, fontWeight: '800', color: colors.ink },
  mrp: { fontSize: 11, color: colors.inkFaint, textDecorationLine: 'line-through' },
  caseRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 6,
  },
  caseText: { flexShrink: 1, fontSize: 10, color: colors.inkMuted },
  caseAdd: { fontSize: 11, fontWeight: '800', color: colors.green },
});
