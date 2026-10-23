import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius } from '@/lib/theme';

/** "Today's deals" hero banner. Renders nothing when there's no deal to advertise. */
export function PromoBanner({
  offerCount,
  promoText,
  bestOff,
  onPress,
}: {
  offerCount: number;
  promoText?: string;
  bestOff: number;
  onPress: () => void;
}) {
  if (offerCount === 0 && bestOff === 0) return null;
  const title = offerCount > 0 ? `${offerCount} item${offerCount === 1 ? '' : 's'} on offer` : `Up to ${bestOff}% below MRP`;
  const subtitle =
    offerCount > 0 ? (promoText ?? 'Special store discounts this week') : 'Wholesale rates on every item — GST bill included';
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.banner, pressed && { opacity: 0.92 }]}>
      <View style={{ flex: 1 }}>
        <Text style={styles.eyebrow}>TODAY'S DEALS</Text>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.subtitle} numberOfLines={2}>
          {subtitle}
        </Text>
        <View style={styles.cta}>
          <Text style={styles.ctaText}>Shop deals</Text>
          <Ionicons name="arrow-forward" size={14} color={colors.brand} />
        </View>
      </View>
      <View style={styles.badge}>
        <Text style={styles.badgeBig}>{bestOff}%</Text>
        <Text style={styles.badgeSmall}>OFF</Text>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  banner: {
    backgroundColor: colors.brand,
    borderRadius: radius.lg,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  eyebrow: { color: 'rgba(255,255,255,0.8)', fontSize: 10, fontWeight: '900', letterSpacing: 1.2 },
  title: { marginTop: 4, color: '#fff', fontSize: 20, fontWeight: '900' },
  subtitle: { marginTop: 4, color: 'rgba(255,255,255,0.9)', fontSize: 12 },
  cta: {
    marginTop: 12,
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 14,
  },
  ctaText: { color: colors.brand, fontWeight: '800', fontSize: 12 },
  badge: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: '#FFD43B',
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '-8deg' }],
  },
  badgeBig: { fontSize: 22, fontWeight: '900', color: colors.ink },
  badgeSmall: { fontSize: 11, fontWeight: '900', color: colors.ink, marginTop: -2 },
});
