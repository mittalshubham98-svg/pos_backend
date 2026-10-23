import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  RefreshControl,
  StyleSheet,
  Text,
  TextInput,
  useWindowDimensions,
  View,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';

import { CartBar } from '@/components/CartBar';
import { ProductCard } from '@/components/ProductCard';
import { api, Catalog, CatalogItem } from '@/lib/api';
import { percentOff } from '@/lib/format';
import { colors, radius } from '@/lib/theme';
import { useAuth } from '@/state/auth';

const ALL = 'All';
const DEALS = 'Top deals';
const GAP = 12;

export default function HomeScreen() {
  const auth = useAuth();
  const { width } = useWindowDimensions();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [category, setCategory] = useState(ALL);
  const [query, setQuery] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);

  const load = useCallback(async () => {
    try {
      setError(null);
      setCatalog(await api.catalog(auth.apiUrl));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load the catalogue');
    }
  }, [auth.apiUrl]);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  }, [load]);

  const offers = useMemo(() => catalog?.items.filter((i) => i.on_offer) ?? [], [catalog]);
  const bestOff = useMemo(
    () => (catalog?.items ?? []).reduce((best, i) => Math.max(best, percentOff(i.mrp, i.selling_price)), 0),
    [catalog],
  );

  const visible = useMemo(() => {
    if (!catalog) return [];
    let items: CatalogItem[] = catalog.items;
    if (category === DEALS) {
      items = [...items]
        .filter((i) => i.on_offer || percentOff(i.mrp, i.selling_price) > 0)
        .sort((a, b) => Number(b.on_offer) - Number(a.on_offer) || percentOff(b.mrp, b.selling_price) - percentOff(a.mrp, a.selling_price));
    } else if (category !== ALL) {
      items = items.filter((i) => i.category === category);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      items = items.filter((i) => [i.name, i.brand, i.category].some((f) => f?.toLowerCase().includes(q)));
    }
    return items;
  }, [catalog, category, query]);

  // Item count per dropdown option, so customers can see how big each category is.
  const counts = useMemo(() => {
    const map: Record<string, number> = { [ALL]: catalog?.items.length ?? 0 };
    map[DEALS] = (catalog?.items ?? []).filter((i) => i.on_offer || percentOff(i.mrp, i.selling_price) > 0).length;
    for (const i of catalog?.items ?? []) if (i.category) map[i.category] = (map[i.category] ?? 0) + 1;
    return map;
  }, [catalog]);

  const cardWidth = (width - GAP * 3) / 2;
  const chips = [ALL, DEALS, ...(catalog?.categories ?? [])];
  const firstName = (auth.session?.name ?? '').split(' ')[0];

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>PILANI SUPPLY CO.</Text>
        <Text style={styles.greeting} numberOfLines={1}>
          {firstName ? `Hi ${firstName}, what do you need today?` : 'What do you need today?'}
        </Text>
        <View style={styles.search}>
          <Ionicons name="search" size={18} color={colors.inkMuted} />
          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder="Search atta, oil, dal…"
            placeholderTextColor={colors.inkFaint}
            style={styles.searchInput}
            returnKeyType="search"
            autoCorrect={false}
          />
          {query.length > 0 && (
            <Pressable onPress={() => setQuery('')} hitSlop={10} accessibilityLabel="Clear search">
              <Ionicons name="close-circle" size={18} color={colors.inkFaint} />
            </Pressable>
          )}
        </View>
      </View>

      <View style={styles.dropdownBar}>
        <Pressable
          onPress={() => setPickerOpen(true)}
          style={({ pressed }) => [styles.dropdown, pressed && { opacity: 0.8 }]}
          accessibilityRole="button"
          accessibilityLabel={`Category: ${titleCase(category)}. Tap to change`}
        >
          <Ionicons name={category === DEALS ? 'pricetag' : 'grid-outline'} size={16} color={colors.brand} />
          <Text style={styles.dropdownLabel}>Category</Text>
          <Text style={styles.dropdownValue} numberOfLines={1}>
            {titleCase(category)}
          </Text>
          <Ionicons name="chevron-down" size={18} color={colors.ink} />
        </Pressable>
      </View>

      <CategoryPicker
        visible={pickerOpen}
        options={chips}
        selected={category}
        counts={counts}
        onSelect={(c) => {
          setCategory(c);
          setPickerOpen(false);
        }}
        onClose={() => setPickerOpen(false)}
      />

      {!catalog && !error ? (
        <View style={styles.center}>
          <ActivityIndicator color={colors.brand} size="large" />
        </View>
      ) : error && !catalog ? (
        <View style={styles.center}>
          <Ionicons name="cloud-offline-outline" size={40} color={colors.inkFaint} />
          <Text style={styles.errorText}>{error}</Text>
          <Pressable onPress={load} style={styles.retry}>
            <Text style={styles.retryText}>Try again</Text>
          </Pressable>
        </View>
      ) : (
        <FlatList
          data={visible}
          keyExtractor={(i) => String(i.id)}
          numColumns={2}
          columnWrapperStyle={{ gap: GAP }}
          contentContainerStyle={styles.grid}
          keyboardDismissMode="on-drag"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brand} />}
          ListHeaderComponent={
            category === ALL && !query ? (
              <PromoBanner
                offerCount={offers.length}
                promoText={offers.find((o) => o.promo_status)?.promo_status}
                bestOff={bestOff}
                onPress={() => setCategory(DEALS)}
              />
            ) : (
              <Text style={styles.resultCount}>
                {visible.length} item{visible.length === 1 ? '' : 's'}
              </Text>
            )
          }
          ListEmptyComponent={
            <View style={styles.center}>
              <Text style={styles.emptyTitle}>Nothing matched</Text>
              <Text style={styles.emptyText}>Add it as an unlisted item at checkout and the store will source it.</Text>
            </View>
          }
          renderItem={({ item }) => <ProductCard item={item} apiUrl={auth.apiUrl} width={cardWidth} />}
          initialNumToRender={8}
          windowSize={7}
        />
      )}

      <CartBar label="View cart" onPress={() => router.navigate('/cart')} />
    </SafeAreaView>
  );
}

function PromoBanner({
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
  const title = offerCount > 0 ? `${offerCount} item${offerCount === 1 ? '' : 's'} on offer` : `Up to ${bestOff}% below MRP`;
  const subtitle =
    offerCount > 0 ? (promoText ?? 'Special store discounts this week') : 'Wholesale rates on every item — GST bill included';
  if (offerCount === 0 && bestOff === 0) return null;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [styles.banner, pressed && { opacity: 0.92 }]}>
      <View style={{ flex: 1 }}>
        <Text style={styles.bannerEyebrow}>TODAY'S DEALS</Text>
        <Text style={styles.bannerTitle}>{title}</Text>
        <Text style={styles.bannerSubtitle} numberOfLines={2}>
          {subtitle}
        </Text>
        <View style={styles.bannerCta}>
          <Text style={styles.bannerCtaText}>Shop deals</Text>
          <Ionicons name="arrow-forward" size={14} color={colors.brand} />
        </View>
      </View>
      <View style={styles.bannerBadge}>
        <Text style={styles.bannerBadgeBig}>{bestOff}%</Text>
        <Text style={styles.bannerBadgeSmall}>OFF</Text>
      </View>
    </Pressable>
  );
}

/** Bottom-sheet style dropdown listing every category with its item count. */
function CategoryPicker({
  visible,
  options,
  selected,
  counts,
  onSelect,
  onClose,
}: {
  visible: boolean;
  options: string[];
  selected: string;
  counts: Record<string, number>;
  onSelect: (category: string) => void;
  onClose: () => void;
}) {
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Close categories" />
      <View style={[styles.sheet, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        <View style={styles.sheetHandle} />
        <View style={styles.sheetHeader}>
          <Text style={styles.sheetTitle}>Choose a category</Text>
          <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close">
            <Ionicons name="close" size={22} color={colors.ink} />
          </Pressable>
        </View>
        <FlatList
          data={options}
          keyExtractor={(c) => c}
          renderItem={({ item: c }) => {
            const active = c === selected;
            return (
              <Pressable
                onPress={() => onSelect(c)}
                style={({ pressed }) => [styles.option, active && styles.optionActive, pressed && { opacity: 0.7 }]}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
              >
                {c === DEALS && <Ionicons name="pricetag" size={14} color={colors.brand} />}
                <Text style={[styles.optionText, active && styles.optionTextActive]} numberOfLines={1}>
                  {titleCase(c)}
                </Text>
                <Text style={styles.optionCount}>{counts[c] ?? 0}</Text>
                {active ? (
                  <Ionicons name="checkmark-circle" size={20} color={colors.brand} />
                ) : (
                  <View style={{ width: 20 }} />
                )}
              </Pressable>
            );
          }}
        />
      </View>
    </Modal>
  );
}

function titleCase(s: string): string {
  if (s === ALL || s === DEALS) return s;
  return s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 10, backgroundColor: colors.card },
  eyebrow: { fontSize: 11, fontWeight: '900', color: colors.brand, letterSpacing: 1 },
  greeting: { marginTop: 2, fontSize: 18, fontWeight: '800', color: colors.ink },
  search: {
    marginTop: 12,
    height: 44,
    borderRadius: radius.md,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.line,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 8,
  },
  searchInput: { flex: 1, fontSize: 15, color: colors.ink, paddingVertical: 0 },
  dropdownBar: {
    paddingHorizontal: 16,
    paddingBottom: 12,
    backgroundColor: colors.card,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  dropdown: {
    height: 44,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.card,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    gap: 8,
  },
  dropdownLabel: { fontSize: 13, color: colors.inkMuted },
  dropdownValue: { flex: 1, fontSize: 15, fontWeight: '800', color: colors.ink },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },
  sheet: {
    maxHeight: '75%',
    backgroundColor: colors.card,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingTop: 8,
  },
  sheetHandle: { alignSelf: 'center', width: 40, height: 4, borderRadius: 2, backgroundColor: colors.line },
  sheetHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  sheetTitle: { fontSize: 17, fontWeight: '900', color: colors.ink },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
  },
  optionActive: { backgroundColor: colors.brandTint },
  optionText: { flex: 1, fontSize: 15, color: colors.ink },
  optionTextActive: { fontWeight: '800', color: colors.brand },
  optionCount: { fontSize: 12, color: colors.inkFaint, fontWeight: '700' },
  grid: { padding: GAP, gap: GAP, paddingBottom: 96 },
  resultCount: { fontSize: 12, color: colors.inkMuted, fontWeight: '700' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 10 },
  errorText: { textAlign: 'center', color: colors.inkMuted, fontSize: 14 },
  retry: { marginTop: 6, paddingHorizontal: 18, paddingVertical: 10, borderRadius: radius.sm, backgroundColor: colors.brand },
  retryText: { color: '#fff', fontWeight: '800' },
  emptyTitle: { fontSize: 16, fontWeight: '800', color: colors.ink },
  emptyText: { fontSize: 13, color: colors.inkMuted, textAlign: 'center' },
  banner: {
    backgroundColor: colors.brand,
    borderRadius: radius.lg,
    padding: 16,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  bannerEyebrow: { color: 'rgba(255,255,255,0.8)', fontSize: 10, fontWeight: '900', letterSpacing: 1.2 },
  bannerTitle: { marginTop: 4, color: '#fff', fontSize: 20, fontWeight: '900' },
  bannerSubtitle: { marginTop: 4, color: 'rgba(255,255,255,0.9)', fontSize: 12 },
  bannerCta: {
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
  bannerCtaText: { color: colors.brand, fontWeight: '800', fontSize: 12 },
  bannerBadge: {
    width: 76,
    height: 76,
    borderRadius: 38,
    backgroundColor: '#FFD43B',
    alignItems: 'center',
    justifyContent: 'center',
    transform: [{ rotate: '-8deg' }],
  },
  bannerBadgeBig: { fontSize: 22, fontWeight: '900', color: colors.ink },
  bannerBadgeSmall: { fontSize: 11, fontWeight: '900', color: colors.ink, marginTop: -2 },
});
