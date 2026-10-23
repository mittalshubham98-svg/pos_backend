import { Image } from 'expo-image';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { categoryIcon } from '@/lib/categoryIcon';
import { colors } from '@/lib/theme';

/** Item photo on a soft grey plate, or the category's icon when there's no photo yet. */
export function ProductImage({
  uri,
  name,
  category,
  size,
}: {
  uri: string | null;
  name: string;
  category?: string | null;
  size: number;
}) {
  const [failed, setFailed] = useState(false);
  return (
    <View style={[styles.plate, { width: size, height: size }]}>
      {uri && !failed ? (
        <Image
          source={{ uri }}
          style={{ width: size * 0.86, height: size * 0.86 }}
          contentFit="contain"
          transition={150}
          onError={() => setFailed(true)}
          accessibilityLabel={name}
        />
      ) : (
        <Text style={{ fontSize: size * 0.42 }} accessibilityLabel={name}>
          {categoryIcon(category)}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  plate: { borderRadius: 12, backgroundColor: colors.imageBg, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
});
