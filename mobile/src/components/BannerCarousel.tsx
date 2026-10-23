import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { FlatList, NativeScrollEvent, NativeSyntheticEvent, Pressable, StyleSheet, View } from 'react-native';

import { Banner } from '@/lib/api';
import { colors, radius } from '@/lib/theme';

const AUTO_ADVANCE_MS = 4000;

/** Swipeable, auto-advancing carousel of the banners uploaded in the admin portal. */
export function BannerCarousel({
  banners,
  apiUrl,
  width,
  onPress,
}: {
  banners: Banner[];
  apiUrl: string;
  width: number;
  onPress: (banner: Banner) => void;
}) {
  const listRef = useRef<FlatList<Banner>>(null);
  const [index, setIndex] = useState(0);
  const height = Math.round(width / 2); // banners are designed at 2:1

  // Auto-advance; restarts after every manual swipe because `index` changes.
  useEffect(() => {
    if (banners.length < 2) return;
    const timer = setTimeout(() => {
      const next = (index + 1) % banners.length;
      listRef.current?.scrollToOffset({ offset: next * width, animated: true });
      setIndex(next);
    }, AUTO_ADVANCE_MS);
    return () => clearTimeout(timer);
  }, [index, banners.length, width]);

  const onScrollEnd = (e: NativeSyntheticEvent<NativeScrollEvent>) =>
    setIndex(Math.round(e.nativeEvent.contentOffset.x / width));

  return (
    <View>
      <FlatList
        ref={listRef}
        data={banners}
        keyExtractor={(b) => String(b.id)}
        horizontal
        pagingEnabled
        showsHorizontalScrollIndicator={false}
        onMomentumScrollEnd={onScrollEnd}
        onScrollEndDrag={onScrollEnd}
        getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
        style={{ width, borderRadius: radius.lg }}
        renderItem={({ item }) => (
          <Pressable
            onPress={() => onPress(item)}
            disabled={!item.link}
            accessibilityRole={item.link ? 'button' : 'image'}
            accessibilityLabel={item.title || 'Store banner'}
          >
            <Image
              source={{ uri: apiUrl + item.image_url }}
              style={{ width, height, backgroundColor: colors.brandTint }}
              contentFit="cover"
              transition={200}
            />
          </Pressable>
        )}
      />
      {banners.length > 1 && (
        <View style={styles.dots}>
          {banners.map((b, i) => (
            <View key={b.id} style={[styles.dot, i === index && styles.dotActive]} />
          ))}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  dots: { flexDirection: 'row', justifyContent: 'center', gap: 6, marginTop: 8 },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: colors.line },
  dotActive: { width: 18, backgroundColor: colors.brand },
});
