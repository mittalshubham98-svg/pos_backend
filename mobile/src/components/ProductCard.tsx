import { memo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ProductImage } from '@/components/ProductImage';
import { QtyStepper } from '@/components/QtyStepper';
import { CatalogItem, imageUrl } from '@/lib/api';
import { percentOff, rupees } from '@/lib/format';
import { colors, radius } from '@/lib/theme';
import { lineKey, useCart } from '@/state/cart';

type Props = { item: CatalogItem; apiUrl: string; width: number };

/** Quick-commerce product tile: % OFF and size tags, name, brand, price with struck-through
 *  MRP, and a green ADD that turns into a stepper. Shows the item's photo only if one has
 *  been uploaded. */
function ProductCardBase({ item, apiUrl, width }: Props) {
  const cart = useCart();
  const qty = cart.qtyOf(item.id, 'PCS');
  const caseQty = cart.qtyOf(item.id, 'CASE');
  const off = percentOff(item.mrp, item.selling_price);
  // Capped so tablets / wide windows don't get poster-sized tiles.
  const imageSize = Math.min(width - 16, 180);

  return (
    <View style={[styles.card, { width }]}>
      {/* Only an uploaded photo is shown — no placeholder art for items without one. */}
      <View style={{ alignSelf: 'center' }}>
        <ProductImage uri={imageUrl(apiUrl, item.image_url)} name={item.name} size={imageSize} />
      </View>

      <View style={styles.body}>
        <View style={styles.tags}>
          {off > 0 && (
            <View style={styles.offPill}>
              <Text style={styles.offPillText}>{off}% OFF</Text>
            </View>
          )}
          {item.size ? (
            <View style={styles.sizePill}>
              <Text style={styles.sizeText} numberOfLines={1}>
                {item.size}
              </Text>
            </View>
          ) : null}
        </View>
        <Text style={styles.name} numberOfLines={2}>
          {item.name}
        </Text>
        {item.brand ? (
          <Text style={styles.brand} numberOfLines={1}>
            {item.brand}
          </Text>
        ) : null}
        {item.promo_status ? (
          <Text style={styles.promo} numberOfLines={1}>
            {item.promo_status}
          </Text>
        ) : null}

        <View style={styles.footer}>
          <View style={{ flexShrink: 1 }}>
            {item.selling_price > 0 ? (
              <>
                <Text style={styles.price}>{rupees(item.selling_price)}</Text>
                {item.mrp > item.selling_price && <Text style={styles.mrp}>{rupees(item.mrp)}</Text>}
              </>
            ) : (
              // No rate set in the catalogue yet — still orderable, the store prices it on the bill.
              <Text style={styles.onRequest}>Price on{'\n'}request</Text>
            )}
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
    </View>
  );
}

export const ProductCard = memo(ProductCardBase);

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 8,
    borderWidth: 1,
    borderColor: colors.line,
  },
  body: { paddingHorizontal: 4, paddingTop: 4 },
  tags: { flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginBottom: 6, minHeight: 18 },
  offPill: { backgroundColor: colors.blue, borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  offPillText: { color: '#fff', fontSize: 10, fontWeight: '900' },
  sizePill: { backgroundColor: colors.imageBg, borderRadius: 4, paddingHorizontal: 5, paddingVertical: 2 },
  sizeText: { fontSize: 10, fontWeight: '700', color: colors.inkMuted },
  name: { fontSize: 13, fontWeight: '700', color: colors.ink, minHeight: 34, lineHeight: 17 },
  brand: { marginTop: 2, fontSize: 11, color: colors.inkFaint },
  promo: {
    marginTop: 4,
    alignSelf: 'flex-start',
    backgroundColor: colors.yellowTint,
    color: colors.amber,
    fontSize: 10,
    fontWeight: '800',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    overflow: 'hidden',
  },
  footer: { marginTop: 10, flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', gap: 6 },
  price: { fontSize: 14, fontWeight: '900', color: colors.ink },
  mrp: { fontSize: 11, color: colors.inkFaint, textDecorationLine: 'line-through' },
  onRequest: { fontSize: 11, fontWeight: '700', color: colors.amber, lineHeight: 14 },
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
