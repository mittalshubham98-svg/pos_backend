import { Ionicons } from '@expo/vector-icons';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';

import { ProductImage } from '@/components/ProductImage';
import { imageUrl, PurchasedItem } from '@/lib/api';
import { colors, radius, shadow } from '@/lib/theme';

/** Home-screen card previewing the customer's most-bought items; tapping opens the full
 *  most-to-least list. New customers see a hint instead. */
export function RegularsCard({
  items,
  error,
  apiUrl,
  onPress,
  onRetry,
}: {
  items: PurchasedItem[] | null;
  error: string | null;
  apiUrl: string;
  onPress: () => void;
  onRetry: () => void;
}) {
  if (items === null && error) {
    return (
      <View style={styles.card}>
        <View style={styles.head}>
          <Ionicons name="repeat" size={18} color={colors.brand} />
          <Text style={styles.title}>Your regular items</Text>
        </View>
        <Text style={styles.sub}>{error}</Text>
        <Pressable onPress={onRetry} hitSlop={8} accessibilityRole="button">
          <Text style={styles.seeAll}>Try again</Text>
        </Pressable>
      </View>
    );
  }
  if (items === null) {
    return (
      <View style={[styles.card, { alignItems: 'center', paddingVertical: 28 }]}>
        <ActivityIndicator color={colors.brand} />
      </View>
    );
  }
  if (items.length === 0) {
    return (
      <View style={styles.card}>
        <View style={styles.head}>
          <Ionicons name="repeat" size={18} color={colors.brand} />
          <Text style={styles.title}>Your regular items</Text>
        </View>
        <Text style={styles.sub}>Items you order will appear here, most bought first, so you can reorder in one tap.</Text>
      </View>
    );
  }
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.card, pressed && { opacity: 0.9 }]}
      accessibilityRole="button"
      accessibilityLabel={`Your regular items, ${items.length} items. Open list`}
    >
      <View style={styles.head}>
        <Ionicons name="repeat" size={18} color={colors.brand} />
        <Text style={styles.title}>Your regular items</Text>
        <Text style={styles.seeAll}>See all {items.length}</Text>
        <Ionicons name="chevron-forward" size={16} color={colors.brand} />
      </View>
      <Text style={styles.sub}>Most bought first — tap to reorder quickly</Text>
      <View style={styles.row}>
        {items.slice(0, 4).map((item, rank) => (
          <View key={item.id} style={styles.item}>
            <View>
              <ProductImage uri={imageUrl(apiUrl, item.image_url)} name={item.name} size={64} />
              <View style={styles.rankBadge}>
                <Text style={styles.rankText}>{rank + 1}</Text>
              </View>
            </View>
            <Text style={styles.name} numberOfLines={2}>
              {item.name}
            </Text>
          </View>
        ))}
        {/* Keep preview tiles a fixed width when there are fewer than four items. */}
        {Array.from({ length: Math.max(0, 4 - items.length) }, (_, i) => (
          <View key={`pad-${i}`} style={styles.item} />
        ))}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: { backgroundColor: colors.card, borderRadius: radius.lg, padding: 14, gap: 6, ...shadow },
  head: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  title: { flex: 1, fontSize: 16, fontWeight: '900', color: colors.ink },
  seeAll: { fontSize: 13, fontWeight: '800', color: colors.brand },
  sub: { fontSize: 12, color: colors.inkMuted },
  row: { flexDirection: 'row', gap: 10, marginTop: 6 },
  item: { flex: 1, alignItems: 'center', gap: 4 },
  name: { fontSize: 11, color: colors.ink, textAlign: 'center' },
  rankBadge: {
    position: 'absolute',
    top: -6,
    left: -6,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: colors.ink,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankText: { color: '#fff', fontSize: 11, fontWeight: '900' },
});
