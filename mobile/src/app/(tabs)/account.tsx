import { Ionicons } from '@expo/vector-icons';
import Constants from 'expo-constants';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';
import { useCart } from '@/state/cart';

export default function AccountScreen() {
  const auth = useAuth();
  const cart = useCart();
  const name = auth.session?.name ?? 'Customer';
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? '')
    .join('');

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.title}>Account</Text>
      </View>

      <View style={styles.profile}>
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>{initials || '?'}</Text>
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.name}>{name}</Text>
          <Text style={styles.code}>Customer ID · {auth.session?.custCode}</Text>
        </View>
      </View>

      <View style={styles.card}>
        <InfoRow icon="server-outline" label="Store server" value={auth.apiUrl.replace(/^https?:\/\//, '')} />
        <InfoRow icon="information-circle-outline" label="App version" value={Constants.expoConfig?.version ?? '—'} />
      </View>

      <Pressable
        onPress={() => {
          cart.clear();
          auth.signOut();
        }}
        style={({ pressed }) => [styles.signOut, pressed && { opacity: 0.8 }]}
        accessibilityRole="button"
      >
        <Ionicons name="log-out-outline" size={18} color={colors.brand} />
        <Text style={styles.signOutText}>Sign out</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function InfoRow({ icon, label, value }: { icon: keyof typeof Ionicons.glyphMap; label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={18} color={colors.inkMuted} />
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue} numberOfLines={1}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  header: { paddingHorizontal: 16, paddingVertical: 12, backgroundColor: colors.card },
  title: { fontSize: 20, fontWeight: '900', color: colors.ink },
  profile: {
    margin: 12,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    backgroundColor: colors.card,
    borderRadius: radius.md,
    padding: 16,
    ...shadow,
  },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { color: '#fff', fontSize: 20, fontWeight: '900' },
  name: { fontSize: 18, fontWeight: '800', color: colors.ink },
  code: { marginTop: 2, fontSize: 13, color: colors.inkMuted },
  card: { marginHorizontal: 12, backgroundColor: colors.card, borderRadius: radius.md, paddingHorizontal: 16, ...shadow },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  rowLabel: { fontSize: 14, color: colors.ink, flex: 1 },
  rowValue: { fontSize: 13, color: colors.inkMuted, maxWidth: '55%' },
  signOut: {
    margin: 12,
    marginTop: 20,
    height: 48,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: colors.brand,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: colors.card,
  },
  signOutText: { color: colors.brand, fontWeight: '800', fontSize: 15 },
});
