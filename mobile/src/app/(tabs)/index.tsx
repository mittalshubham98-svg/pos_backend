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
import { DEALS } from '@/lib/catalog';
import { percentOff } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { usePurchasedItems } from '@/lib/usePurchasedItems';
import { useAuth } from '@/state/auth';

/** Home: the customer's own regular items up front; the full catalogue lives in its own tab. */
export default function HomeScreen() {
  const auth = useAuth();
  const purchased = usePurchasedItems();
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [banners, setBanners] = useState<Banner[]>([]);
  const [bannerWidth, setBannerWidth] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  // Banners uploaded in the admin portal, plus the catalogue for the automatic deals
  // banner shown when there are none. A failure just hides that part.
  const loadCatalog = useCallback(async () => {
    const [cat, ban] = await Promise.allSettled([api.catalog(auth.apiUrl), api.banners(auth.apiUrl)]);
    setCatalog(cat.status === 'fulfilled' ? cat.value : null);
    setBanners(ban.status === 'fulfilled' ? ban.value : []);
  }, [auth.apiUrl]);

  const openBanner = (b: Banner) => {
    if (b.link === 'deals') router.navigate({ pathname: '/catalogue', params: { category: DEALS } });
    else if (b.link === 'catalogue') router.navigate('/catalogue');
    else if (b.link.startsWith('category:'))
      router.navigate({ pathname: '/catalogue', params: { category: b.link.slice('category:'.length) } });
  };

  useEffect(() => {
    loadCatalog();
  }, [loadCatalog]);

  const offers = useMemo(() => catalog?.items.filter((i) => i.on_offer) ?? [], [catalog]);
  const bestOff = useMemo(
    () => (catalog?.items ?? []).reduce((best, i) => Math.max(best, percentOff(i.mrp, i.selling_price)), 0),
    [catalog],
  );
  const firstName = (auth.session?.name ?? '').split(' ')[0];

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.eyebrow}>PILANI SUPPLY CO.</Text>
        <Text style={styles.greeting} numberOfLines={1}>
          {firstName ? `Hi ${firstName}, what do you need today?` : 'What do you need today?'}
        </Text>
      </View>

      <ScrollView
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
            onPress={() => router.navigate({ pathname: '/catalogue', params: { category: DEALS } })}
          />
          )
        )}

        <RegularsCard
          items={purchased.items}
          error={purchased.error}
          apiUrl={auth.apiUrl}
          onPress={() => router.push('/regulars')}
          onRetry={purchased.reload}
        />

        <Pressable
          onPress={() => router.navigate('/catalogue')}
          style={({ pressed }) => [styles.browse, pressed && { opacity: 0.9 }]}
          accessibilityRole="button"
        >
          <View style={styles.browseIcon}>
            <Ionicons name="grid" size={22} color={colors.brand} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.browseTitle}>Browse full catalogue</Text>
            <Text style={styles.browseSub}>
              {catalog ? `${catalog.items.length} items in ${catalog.categories.length} categories` : 'Search and shop by category'}
            </Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color={colors.inkMuted} />
        </Pressable>

        <UnlistedBox />
      </ScrollView>

      <CartBar label="View cart" onPress={() => router.navigate('/cart')} />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingTop: 8, paddingBottom: 12, backgroundColor: colors.card },
  eyebrow: { fontSize: 11, fontWeight: '900', color: colors.brand, letterSpacing: 1 },
  greeting: { marginTop: 2, fontSize: 18, fontWeight: '800', color: colors.ink },
  content: { padding: 12, gap: 12, paddingBottom: 96 },
  browse: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    backgroundColor: colors.card,
    borderRadius: radius.lg,
    padding: 14,
    ...shadow,
  },
  browseIcon: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.brandTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  browseTitle: { fontSize: 15, fontWeight: '900', color: colors.ink },
  browseSub: { marginTop: 2, fontSize: 12, color: colors.inkMuted },
});
