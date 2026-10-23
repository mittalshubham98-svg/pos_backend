import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import { colors, radius, shadow } from '@/lib/theme';
import { useCart } from '@/state/cart';

/** "Items not in the list" box. Bound to the cart, so text typed on Home, in the Cart or at
 *  checkout is the same request and goes out with the next order. */
export function UnlistedBox({ title = "Can't find something?" }: { title?: string }) {
  const cart = useCart();
  return (
    <View style={styles.card}>
      <View style={styles.head}>
        <Ionicons name="create-outline" size={18} color={colors.brand} />
        <Text style={styles.title}>{title}</Text>
        {cart.unlisted.length > 0 && (
          <Pressable onPress={() => cart.setUnlisted('')} hitSlop={10} accessibilityLabel="Clear unlisted items">
            <Text style={styles.clear}>Clear</Text>
          </Pressable>
        )}
      </View>
      <Text style={styles.sub}>Write items that aren't in the catalogue — the store will source them for you.</Text>
      <TextInput
        value={cart.unlisted}
        onChangeText={cart.setUnlisted}
        placeholder={'One item per line — brand, size, quantity\ne.g. Kabuli chana 1kg — 5 packets'}
        placeholderTextColor={colors.inkFaint}
        multiline
        textAlignVertical="top"
        style={styles.input}
        accessibilityLabel="Items not in the list"
      />
      {cart.unlisted.trim().length > 0 && (
        <Text style={styles.note}>
          <Ionicons name="checkmark-circle" size={12} color={colors.green} /> Added — sent with your next order
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, gap: 8, ...shadow },
  head: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { flex: 1, fontSize: 16, fontWeight: '900', color: colors.ink },
  clear: { fontSize: 13, fontWeight: '700', color: colors.brand },
  sub: { fontSize: 12, color: colors.inkMuted },
  input: {
    minHeight: 96,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.sm,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 10,
    fontSize: 14,
    color: colors.ink,
  },
  note: { fontSize: 12, color: colors.green, fontWeight: '700' },
});
