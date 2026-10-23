import { Ionicons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { BannerCarousel } from '@/components/BannerCarousel';
import { CartBar } from '@/components/CartBar';
import { PromoBanner } from '@/components/PromoBanner';
import { RegularsCard } from '@/components/RegularsCard';
import { UnlistedBox } from '@/components/UnlistedBox';
import { api, Banner, Catalog } from '@/lib/api';
import { ALL, DEALS, titleCase } from '@/lib/catalog';
import { categoryIcon } from '@/lib/categoryIcon';
import { percentOff } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { usePurchasedItems } from '@/lib/usePurchasedItems';
import { useAuth } from '@/state/auth';

/** Home: deals banner, the customer's regular items, a category strip into the catalogue
 *  and the items-not-in-the-list box. The full catalogue lives in its own tab. */
export default function HomeScreen() {
  const auth = useAuth();
  const purchased = usePurchasedItems();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [banners, setBanners] = useState<Banner[]>([]);
  const [bannerWidth, setBannerWidth] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  // Banners uploaded in the admin portal, plus the catalogue for the automatic deals
  // banner (shown when there are none) and the category strip. A failure just hides that part.
  const loadCatalog = useCallback(async () => {
    const [cat, ban] = await Promise.allSettled([api.catalog(auth.apiUrl), api.banners(auth.apiUrl)]);
    setCatalog(cat.status === 'fulfilled' ? cat.value : null);
    setBanners(ban.status === 'fulfilled' ? ban.value : []);
  }, [auth.apiUrl]);

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const openCategory = (category: string) => router.navigate({ pathname: '/catalogue', params: { category } });
  const openBanner = (b: Banner) => {
    if (b.link === 'deals') openCategory(DEALS);
    else if (b.link === 'catalogue') router.navigate('/catalogue');
    else if (b.link.startsWith('category:')) openCategory(b.link.slice('category:'.length));
  };

  const offers = useMemo(() => catalog?.items.filter((i) => i.on_offer) ?? [], [catalog]);
  const bestOff = useMemo(
    () => (catalog?.items ?? []).reduce((best, i) => Math.max(best, percentOff(i.mrp, i.selling_price)), 0),
    [catalog],
  );
  const firstName = (auth.session?.name ?? '').split(' ')[0];

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <View style={{ flex: 1 }}>
            <Text style={styles.brandName}>Pilani Supply Co.</Text>
            <Text style={styles.greeting} numberOfLines={1}>
              {firstName ? `Hi ${firstName} · wholesale for your shop` : 'Wholesale grocery for your shop'}
            </Text>
          </View>
          <Pressable
            onPress={() => router.navigate('/account')}
            style={styles.avatar}
            accessibilityRole="button"
            accessibilityLabel="Account"
          >
            <Ionicons name="person" size={20} color={colors.ink} />
          </Pressable>
        </View>
        <Pressable
          onPress={() => router.navigate({ pathname: '/catalogue', params: { focus: String(Date.now()) } })}
          style={styles.search}
          accessibilityRole="search"
          accessibilityLabel="Search the catalogue"
        >
          <Ionicons name="search" size={18} color={colors.inkMuted} />
          <Text style={styles.searchText}>Search "atta", "oil", "dal"…</Text>
        </Pressable>
      </View>

      <ScrollView
        style={{ backgroundColor: colors.bg }}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        automaticallyAdjustKeyboardInsets
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            tintColor={colors.brand}
            onRefresh={async () => {
              setRefreshing(true);
              await Promise.all([loadCatalog(), purchased.reload()]);
              setRefreshing(false);
            }}
          />
        }
      >
        {banners.length > 0 ? (
          <View onLayout={(e) => setBannerWidth(e.nativeEvent.layout.width)}>
            {bannerWidth > 0 && (
              <BannerCarousel banners={banners} apiUrl={auth.apiUrl} width={bannerWidth} onPress={openBanner} />
            )}
          </View>
        ) : (
          catalog && (
            <PromoBanner
              offerCount={offers.length}
              promoText={offers.find((o) => o.promo_status)?.promo_status}
              bestOff={bestOff}
              onPress={() => openCategory(DEALS)}
            />
          )
        )}

        <RegularsCard
          items={purchased.items}
          error={purchased.error}
          onPress={() => router.push('/regulars')}
          onRetry={purchased.reload}
        />

        <View style={styles.section}>
          <View style={styles.sectionHead}>
            <Text style={styles.sectionTitle}>Shop by category</Text>
            <Pressable onPress={() => router.navigate('/catalogue')} hitSlop={8} accessibilityRole="button">
              <Text style={styles.seeAll}>
                {catalog ? `See all ${catalog.items.length} items` : 'Full catalogue'} ›
              </Text>
            </Pressable>
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.catRow}>
            {[ALL, DEALS, ...(catalog?.categories ?? [])].map((c) => (
              <Pressable
                key={c}
                onPress={() => (c === ALL ? router.navigate('/catalogue') : openCategory(c))}
                style={({ pressed }) => [styles.cat, pressed && { opacity: 0.7 }]}
                accessibilityRole="button"
                accessibilityLabel={titleCase(c)}
              >
                <View style={[styles.catCircle, c === DEALS && { backgroundColor: '#E8F0FF' }]}>
                  <Text style={styles.catEmoji}>{categoryIcon(c)}</Text>
                </View>
                <Text style={styles.catName} numberOfLines={2}>
                  {titleCase(c)}
                </Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>

        <UnlistedBox />
      </ScrollView>

      <CartBar label="View cart" onPress={() => router.navigate('/cart')} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.yellow },
  header: { paddingHorizontal: 16, paddingTop: 6, paddingBottom: 14, backgroundColor: colors.yellow, gap: 12 },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  brandName: { fontSize: 22, fontWeight: '900', color: colors.ink, letterSpacing: -0.3 },
  greeting: { marginTop: 1, fontSize: 13, fontWeight: '600', color: '#3D3200' },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.7)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  search: {
    height: 46,
    borderRadius: radius.md,
    backgroundColor: colors.card,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    gap: 10,
    ...shadow,
  },
  searchText: { fontSize: 15, color: colors.inkFaint },
  content: { padding: 12, gap: 14, paddingBottom: 96, backgroundColor: colors.bg, flexGrow: 1 },
  section: { backgroundColor: colors.card, borderRadius: radius.lg, paddingVertical: 14, gap: 12, ...shadow },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14 },
  sectionTitle: { fontSize: 17, fontWeight: '900', color: colors.ink },
  seeAll: { fontSize: 13, fontWeight: '800', color: colors.brand },
  catRow: { paddingHorizontal: 10, gap: 4 },
  cat: { width: 78, alignItems: 'center', gap: 6 },
  catCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.yellowTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  catEmoji: { fontSize: 30 },
  catName: { fontSize: 11, fontWeight: '700', color: colors.ink, textAlign: 'center', lineHeight: 14 },
});
