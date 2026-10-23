import { Image } from 'expo-image';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors } from '@/lib/theme';

/** Item photo, or a tinted monogram tile when the catalogue has no image for it yet. */
export function ProductImage({ uri, name, size }: { uri: string | null; name: string; size: number }) {
  const [failed, setFailed] = useState(false);
  if (uri && !failed) {
    return (
      <Image
        source={{ uri }}
        style={{ width: size, height: size, borderRadius: 10 }}
        contentFit="contain"
        transition={150}
        onError={() => setFailed(true)}
      />
    );
  }
  const initials = name
    .split(/\s+/)
    .filter((w) => /^[A-Za-z]/.test(w))
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join('');
  return (
    <View style={[styles.tile, { width: size, height: size }]}>
      <Text style={[styles.initials, { fontSize: size * 0.3 }]}>{initials || '•'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tile: { borderRadius: 10, backgroundColor: colors.brandTint, alignItems: 'center', justifyContent: 'center' },
  initials: { color: colors.brand, fontWeight: '800' },
});
