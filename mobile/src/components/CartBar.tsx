import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { rupees } from '@/lib/format';
import { colors, radius } from '@/lib/theme';
import { useCart } from '@/state/cart';

/** Sticky bottom bar: item count + running total, tap to continue. Hidden when empty. */
export function CartBar({ label, onPress }: { label: string; onPress: () => void }) {
  const cart = useCart();
  if (!cart.hasAnything) return null;
  const saving = cart.mrpTotal - cart.total;
  const hasUnlisted = cart.unlisted.trim().length > 0;
  // An order can be just an unlisted request, with no catalogue items at all.
  const summary =
    cart.itemCount > 0
      ? `${cart.itemCount} item${cart.itemCount === 1 ? '' : 's'} · ${rupees(Math.round(cart.total))}`
      : 'Unlisted items added';
  return (
    <View style={styles.wrap} pointerEvents="box-none">
      <Pressable
        onPress={onPress}
        style={({ pressed }) => [styles.bar, pressed && { opacity: 0.9 }]}
        accessibilityRole="button"
        accessibilityLabel={`${label}, ${summary}`}
      >
        <View style={styles.bag}>
          <Ionicons name="basket" size={20} color="#fff" />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.count}>{summary}</Text>
          {saving >= 1 ? (
            <Text style={styles.saving}>Saving {rupees(Math.round(saving))} on MRP</Text>
          ) : hasUnlisted && cart.itemCount > 0 ? (
            <Text style={styles.saving}>+ unlisted items</Text>
          ) : null}
        </View>
        <Text style={styles.cta}>{label}</Text>
        <Ionicons name="chevron-forward" size={18} color="#fff" />
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { position: 'absolute', left: 12, right: 12, bottom: 10 },
  bar: {
    backgroundColor: colors.green,
    borderRadius: radius.md,
    paddingVertical: 10,
    paddingHorizontal: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    shadowColor: '#000',
    shadowOpacity: 0.2,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  bag: { backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: 8, padding: 6 },
  count: { color: '#fff', fontWeight: '800', fontSize: 14 },
  saving: { color: 'rgba(255,255,255,0.85)', fontSize: 11, marginTop: 1 },
  cta: { color: '#fff', fontWeight: '800', fontSize: 15 },
});
