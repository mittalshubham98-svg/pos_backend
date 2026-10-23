import { Image } from 'expo-image';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { colors } from '@/lib/theme';

/** The item's own photo (uploaded in the admin portal) on a soft grey plate. Items without
 *  a photo show nothing — no placeholder art — so callers lay out text-only in that case. */
export function ProductImage({ uri, name, size }: { uri: string | null; name: string; size: number }) {
  const [failed, setFailed] = useState(false);
  if (!uri || failed) return null;
  return (
    <View style={[styles.plate, { width: size, height: size }]}>
      <Image
        source={{ uri }}
        style={{ width: size * 0.86, height: size * 0.86 }}
        contentFit="contain"
        transition={150}
        onError={() => setFailed(true)}
        accessibilityLabel={name}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  plate: { borderRadius: 12, backgroundColor: colors.imageBg, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
});
