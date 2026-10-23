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
  const [filterOpen, setFilterOpen] = useState(false);
  const [brands, setBrands] = useState<string[]>([]);
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

  // Each filter narrows independently, so the sheet can count "what you'd get" per option.
  const byQuery = useMemo(() => {
    const q = query.trim().toLowerCase();
    const items = catalog?.items ?? [];
    return q ? items.filter((i) => [i.name, i.brand, i.category].some((f) => f?.toLowerCase().includes(q))) : items;
  }, [catalog, query]);
  const inCategory = useCallback(
    (items: CatalogItem[]) =>
      category === DEALS
        ? items.filter(isDeal).sort(byBestDeal)
        : category !== null && category !== ALL
          ? items.filter((i) => i.category === category)
          : items,
    [category],
  );
  const ofBrands = useCallback(
    (items: CatalogItem[]) => (brands.length ? items.filter((i) => i.brand && brands.includes(i.brand)) : items),
    [brands],
  );
  const visible = useMemo(() => ofBrands(inCategory(byQuery)), [byQuery, inCategory, ofBrands]);

  // Item count per category (within the chosen brands) for the tiles, dropdown and filter sheet.
  const counts = useMemo(() => {
    const items = ofBrands(byQuery);
    const map: Record<string, number> = { [ALL]: items.length, [DEALS]: items.filter(isDeal).length };
    for (const i of items) if (i.category) map[i.category] = (map[i.category] ?? 0) + 1;
    return map;
  }, [byQuery, ofBrands]);

  // Item count per brand within the chosen category.
  const brandCounts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const i of inCategory(byQuery)) if (i.brand) map[i.brand] = (map[i.brand] ?? 0) + 1;
    return map;
  }, [byQuery, inCategory]);

  const cardWidth = (width - GAP * 3) / 2;
  const options = [ALL, DEALS, ...(catalog?.categories ?? [])];
  const activeFilters = brands.length + (category ? 1 : 0);
  const showTiles = category === null && !query.trim() && brands.length === 0;

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Catalogue</Text>
        <View style={styles.searchRow}>
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
            onPress={() => setFilterOpen(true)}
            style={({ pressed }) => [styles.filterBtn, activeFilters > 0 && styles.filterBtnActive, pressed && { opacity: 0.8 }]}
            accessibilityRole="button"
            accessibilityLabel={activeFilters ? `Filters, ${activeFilters} active` : 'Filters'}
          >
            <Ionicons name="options-outline" size={22} color={activeFilters > 0 ? '#fff' : colors.ink} />
            {activeFilters > 0 && (
              <View style={styles.filterBadge}>
                <Text style={styles.filterBadgeText}>{activeFilters}</Text>
              </View>
            )}
          </Pressable>
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

      <FilterSheet
        visible={filterOpen}
        categories={options}
        category={category}
        categoryCounts={counts}
        onCategory={setCategory}
        brands={catalog?.brands ?? []}
        selectedBrands={brands}
        brandCounts={brandCounts}
        onBrands={setBrands}
        resultCount={visible.length}
        onClearAll={() => {
          setCategory(null);
          setBrands([]);
        }}
        onClose={() => setFilterOpen(false)}
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
            <View style={styles.resultRow}>
              <Text style={styles.resultCount} numberOfLines={1}>
                {visible.length} item{visible.length === 1 ? '' : 's'}
                {query.trim() ? ` for “${query.trim()}”` : ''}
                {brands.length ? ` · ${brands.map(titleCase).join(', ')}` : ''}
              </Text>
              {brands.length > 0 && (
                <Pressable onPress={() => setBrands([])} hitSlop={8} accessibilityRole="button">
                  <Text style={styles.clearLink}>Clear brands</Text>
                </Pressable>
              )}
            </View>
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

/** Filter sheet: one category (same choice as the dropdown) and any number of brands. Both
 *  lists come from the live catalogue, so new brands/categories appear as items are imported. */
function FilterSheet({
  visible,
  categories,
  category,
  categoryCounts,
  onCategory,
  brands,
  selectedBrands,
  brandCounts,
  onBrands,
  resultCount,
  onClearAll,
  onClose,
}: {
  visible: boolean;
  categories: string[];
  category: string | null;
  categoryCounts: Record<string, number>;
  onCategory: (c: string | null) => void;
  brands: string[];
  selectedBrands: string[];
  brandCounts: Record<string, number>;
  onBrands: (b: string[]) => void;
  resultCount: number;
  onClearAll: () => void;
  onClose: () => void;
}) {
  const insets = useSafeAreaInsets();
  const [brandQuery, setBrandQuery] = useState('');
  const q = brandQuery.trim().toLowerCase();
  // Selected brands stay listed even if the current category has none of them.
  const shownBrands = brands.filter(
    (b) => (!q || b.toLowerCase().includes(q)) && ((brandCounts[b] ?? 0) > 0 || selectedBrands.includes(b)),
  );
  const toggleBrand = (b: string) =>
    onBrands(selectedBrands.includes(b) ? selectedBrands.filter((x) => x !== b) : [...selectedBrands, b]);

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={styles.backdrop} onPress={onClose} accessibilityLabel="Close filters" />
      <View style={[styles.sheet, styles.filterSheet, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        <View style={styles.sheetHandle} />
        <View style={styles.sheetHeader}>
          <Text style={styles.sheetTitle}>Filters</Text>
          <Pressable onPress={onClearAll} hitSlop={10} accessibilityRole="button">
            <Text style={styles.clearLink}>Clear all</Text>
          </Pressable>
        </View>

        <ScrollView contentContainerStyle={styles.filterBody} keyboardShouldPersistTaps="handled">
          <Text style={styles.filterLabel}>Category</Text>
          <View style={styles.chipWrap}>
            {categories.map((c) => {
              const active = c === category;
              // Hide categories the chosen brands don't sell in (keep the current pick visible).
              if (!active && (categoryCounts[c] ?? 0) === 0) return null;
              return (
                <Pressable
                  key={c}
                  onPress={() => onCategory(active ? null : c)}
                  style={[styles.chip, active && styles.chipActive]}
                  accessibilityRole="button"
                  accessibilityState={{ selected: active }}
                >
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>
                    {titleCase(c)} <Text style={active ? styles.chipTextActive : styles.chipCount}>{categoryCounts[c] ?? 0}</Text>
                  </Text>
                </Pressable>
              );
            })}
          </View>

          <Text style={[styles.filterLabel, { marginTop: 18 }]}>
            Brand{selectedBrands.length ? ` · ${selectedBrands.length} selected` : ''}
          </Text>
          <View style={styles.brandSearch}>
            <Ionicons name="search" size={16} color={colors.inkMuted} />
            <TextInput
              value={brandQuery}
              onChangeText={setBrandQuery}
              placeholder={`Search ${brands.length} brands`}
              placeholderTextColor={colors.inkFaint}
              style={styles.searchInput}
              autoCorrect={false}
            />
          </View>
          <View style={styles.chipWrap}>
            {shownBrands.map((b) => {
              const active = selectedBrands.includes(b);
              return (
                <Pressable
                  key={b}
                  onPress={() => toggleBrand(b)}
                  style={[styles.chip, active && styles.chipActive]}
                  accessibilityRole="checkbox"
                  accessibilityState={{ checked: active }}
                >
                  {active && <Ionicons name="checkmark" size={14} color="#fff" />}
                  <Text style={[styles.chipText, active && styles.chipTextActive]}>
                    {titleCase(b)} <Text style={active ? styles.chipTextActive : styles.chipCount}>{brandCounts[b] ?? 0}</Text>
                  </Text>
                </Pressable>
              );
            })}
            {shownBrands.length === 0 && <Text style={styles.chipCount}>No brands match.</Text>}
          </View>
        </ScrollView>

        <Pressable onPress={onClose} style={styles.applyBtn} accessibilityRole="button">
          <Text style={styles.applyText}>
            Show {resultCount} item{resultCount === 1 ? '' : 's'}
          </Text>
        </Pressable>
      </View>
    </Modal>
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
  searchRow: { flexDirection: 'row', gap: 8 },
  filterBtn: {
    width: 44,
    height: 44,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.card,
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterBtnActive: { backgroundColor: colors.ink, borderColor: colors.ink },
  filterBadge: {
    position: 'absolute',
    top: -6,
    right: -6,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    paddingHorizontal: 5,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  filterBadgeText: { color: '#fff', fontSize: 11, fontWeight: '900' },
  filterSheet: { maxHeight: '85%' },
  filterBody: { paddingHorizontal: 16, paddingBottom: 12 },
  filterLabel: { fontSize: 13, fontWeight: '900', color: colors.ink, marginBottom: 8, letterSpacing: 0.3 },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: colors.card,
  },
  chipActive: { backgroundColor: colors.ink, borderColor: colors.ink },
  chipText: { fontSize: 13, fontWeight: '700', color: colors.ink },
  chipTextActive: { color: '#fff' },
  chipCount: { fontSize: 11, fontWeight: '700', color: colors.inkFaint },
  brandSearch: {
    height: 40,
    borderRadius: radius.sm,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.line,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    gap: 6,
    marginBottom: 10,
  },
  applyBtn: {
    marginHorizontal: 16,
    marginTop: 8,
    height: 48,
    borderRadius: radius.sm,
    backgroundColor: colors.green,
    alignItems: 'center',
    justifyContent: 'center',
  },
  applyText: { color: '#fff', fontSize: 15, fontWeight: '800' },
  resultRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  clearLink: { fontSize: 13, fontWeight: '800', color: colors.brand },
  search: {
    flex: 1,
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
  resultCount: { flex: 1, fontSize: 12, color: colors.inkMuted, fontWeight: '700' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 10 },
  errorText: { textAlign: 'center', color: colors.inkMuted, fontSize: 14 },
  retry: { marginTop: 6, paddingHorizontal: 18, paddingVertical: 10, borderRadius: radius.sm, backgroundColor: colors.brand },
  retryText: { color: '#fff', fontWeight: '800' },
  emptyTitle: { fontSize: 16, fontWeight: '800', color: colors.ink },
  emptyText: { fontSize: 13, color: colors.inkMuted, textAlign: 'center' },
});
