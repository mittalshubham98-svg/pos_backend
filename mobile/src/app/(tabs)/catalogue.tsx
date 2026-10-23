import { Ionicons } from '@expo/vector-icons';
import { router, useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  RefreshControl,
  ScrollView,
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
import { ALL, byBestDeal, DEALS, isDeal, titleCase } from '@/lib/catalog';
import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';

const GAP = 12;

export default function CatalogueScreen() {
  const auth = useAuth();
  const { width } = useWindowDimensions();
  // Home's deals banner opens this tab with ?category=Top deals.
  const params = useLocalSearchParams<{ category?: string }>();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  // null = category tiles; a value = that category's product grid.
  const [category, setCategory] = useState<string | null>(params.category ?? null);
  const [query, setQuery] = useState('');
  const [pickerOpen, setPickerOpen] = useState(false);
  const [tilesWidth, setTilesWidth] = useState(0);

  useEffect(() => {
    if (params.category) setCategory(params.category);
  }, [params.category]);

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

  const visible = useMemo(() => {
    if (!catalog) return [];
    let items: CatalogItem[] = catalog.items;
    if (category === DEALS) {
      items = items.filter(isDeal).sort(byBestDeal);
    } else if (category !== null && category !== ALL) {
      items = items.filter((i) => i.category === category);
    }
    const q = query.trim().toLowerCase();
    if (q) {
      items = items.filter((i) => [i.name, i.brand, i.category].some((f) => f?.toLowerCase().includes(q)));
    }
    return items;
  }, [catalog, category, query]);

  // Item count per category, shown on the tiles and in the dropdown.
  const counts = useMemo(() => {
    const map: Record<string, number> = { [ALL]: catalog?.items.length ?? 0 };
    map[DEALS] = (catalog?.items ?? []).filter(isDeal).length;
    for (const i of catalog?.items ?? []) if (i.category) map[i.category] = (map[i.category] ?? 0) + 1;
    return map;
  }, [catalog]);

  const cardWidth = (width - GAP * 3) / 2;
  const options = [ALL, DEALS, ...(catalog?.categories ?? [])];
  const showTiles = category === null && !query.trim();

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Catalogue</Text>
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
        <Pressable
          onPress={() => setPickerOpen(true)}
          style={({ pressed }) => [styles.dropdown, pressed && { opacity: 0.8 }]}
          accessibilityRole="button"
          accessibilityLabel={category ? `Category: ${titleCase(category)}. Tap to change` : 'Choose a category'}
        >
          <Ionicons name={category === DEALS ? 'pricetag' : 'grid-outline'} size={16} color={colors.brand} />
          <Text style={styles.dropdownLabel}>Category</Text>
          <Text style={[styles.dropdownValue, !category && styles.dropdownPlaceholder]} numberOfLines={1}>
            {category ? titleCase(category) : 'Choose…'}
          </Text>
          {category ? (
            <Pressable onPress={() => setCategory(null)} hitSlop={10} accessibilityLabel="Back to all categories">
              <Ionicons name="close-circle" size={20} color={colors.inkFaint} />
            </Pressable>
          ) : (
            <Ionicons name="chevron-down" size={18} color={colors.ink} />
          )}
        </Pressable>
      </View>

      <CategoryPicker
        visible={pickerOpen}
        options={options}
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
      ) : showTiles ? (
        <ScrollView
          contentContainerStyle={styles.tilesWrap}
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.brand} />}
        >
          <Text style={styles.sectionTitle}>Shop by category</Text>
          <View style={styles.tiles} onLayout={(e) => setTilesWidth(e.nativeEvent.layout.width)}>
            {options.map((c) => (
              <Pressable
                key={c}
                onPress={() => setCategory(c)}
                // Measured container width (not the window's: a web scrollbar eats into it),
                // floored so sub-pixel rounding can't push the third tile onto the next row.
                style={({ pressed }) => [
                  styles.tile,
                  { width: Math.floor(((tilesWidth || width - GAP * 2) - 10 * 2) / 3) },
                  pressed && { opacity: 0.8 },
                ]}
                accessibilityRole="button"
                accessibilityLabel={`${titleCase(c)}, ${counts[c] ?? 0} items`}
              >
                <View style={styles.tileIcon}>
                  {c === ALL ? (
                    <Ionicons name="apps" size={22} color={colors.brand} />
                  ) : c === DEALS ? (
                    <Ionicons name="pricetag" size={20} color={colors.brand} />
                  ) : (
                    <Text style={styles.tileInitial}>{c.trim()[0]?.toUpperCase()}</Text>
                  )}
                </View>
                <Text style={styles.tileName} numberOfLines={2}>
                  {titleCase(c)}
                </Text>
                <Text style={styles.tileCount}>{counts[c] ?? 0} items</Text>
              </Pressable>
            ))}
          </View>
        </ScrollView>
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
            <Text style={styles.resultCount}>
              {visible.length} item{visible.length === 1 ? '' : 's'}
              {query.trim() ? ` for “${query.trim()}”` : ''}
            </Text>
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
  selected: string | null;
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

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
    gap: 10,
    backgroundColor: colors.card,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  title: { fontSize: 20, fontWeight: '900', color: colors.ink },
  search: {
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
  dropdownPlaceholder: { fontWeight: '600', color: colors.inkFaint },
  tilesWrap: { padding: GAP, gap: GAP, paddingBottom: 96 },
  sectionTitle: { fontSize: 16, fontWeight: '900', color: colors.ink },
  tiles: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: {
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 10,
    alignItems: 'center',
    gap: 6,
    ...shadow,
  },
  tileIcon: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tileInitial: { fontSize: 20, fontWeight: '900', color: colors.brand },
  tileName: { fontSize: 12, fontWeight: '700', color: colors.ink, textAlign: 'center', minHeight: 30 },
  tileCount: { fontSize: 10, color: colors.inkFaint, fontWeight: '700' },
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
});
