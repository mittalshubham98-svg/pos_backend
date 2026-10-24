import { Ionicons } from '@expo/vector-icons';
import { Redirect } from 'expo-router';
import { useEffect, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';

export default function LoginScreen() {
  const auth = useAuth();
  const [custCode, setCustCode] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [serverOpen, setServerOpen] = useState(false);
  const [server, setServer] = useState(auth.apiUrl);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The saved server address loads asynchronously after first render.
  useEffect(() => setServer(auth.apiUrl), [auth.apiUrl]);

  if (auth.status === 'signedIn') return <Redirect href="/" />;

  const canSubmit = custCode.trim().length > 0 && password.length > 0 && !busy;

  async function submit() {
    if (!canSubmit) return;
    setBusy(true);
    setError(null);
    try {
      await auth.signIn(server, custCode, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.hero}>
            <View style={styles.logo}>
              <Text style={styles.logoText}>PS</Text>
            </View>
            <Text style={styles.title}>Pilani Supply Co.</Text>
            <Text style={styles.subtitle}>Wholesale grocery ordering for shops & kitchens</Text>
          </View>

          <View style={styles.form}>
            <Text style={styles.label}>Customer ID</Text>
            <TextInput
              value={custCode}
              onChangeText={setCustCode}
              placeholder="e.g. RAMESH01"
              placeholderTextColor={colors.inkFaint}
              autoCapitalize="characters"
              autoCorrect={false}
              autoComplete="username"
              returnKeyType="next"
              style={styles.input}
            />

            <Text style={[styles.label, { marginTop: 16 }]}>Password</Text>
            <View style={styles.passwordRow}>
              <TextInput
                value={password}
                onChangeText={setPassword}
                placeholder="Issued by the store"
                placeholderTextColor={colors.inkFaint}
                secureTextEntry={!showPassword}
                autoCapitalize="none"
                autoCorrect={false}
                autoComplete="password"
                returnKeyType="go"
                onSubmitEditing={submit}
                style={[styles.input, { flex: 1, borderWidth: 0 }]}
              />
              <Pressable
                onPress={() => setShowPassword((s) => !s)}
                hitSlop={10}
                style={styles.eye}
                accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
              >
                <Ionicons name={showPassword ? 'eye-off-outline' : 'eye-outline'} size={20} color={colors.inkMuted} />
              </Pressable>
            </View>

            {error && <Text style={styles.error}>{error}</Text>}

            <Pressable
              onPress={submit}
              disabled={!canSubmit}
              style={({ pressed }) => [styles.button, !canSubmit && { opacity: 0.5 }, pressed && { opacity: 0.85 }]}
              accessibilityRole="button"
            >
              {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Sign in</Text>}
            </Pressable>

            <Text style={styles.help}>Forgot your ID or password? Call the store and we'll reset it.</Text>
          </View>

          <Pressable onPress={() => setServerOpen((o) => !o)} style={styles.serverToggle} hitSlop={8}>
            <Ionicons name="server-outline" size={14} color={colors.inkMuted} />
            <Text style={styles.serverToggleText}>Server: {auth.apiUrl.replace(/^https?:\/\//, '')}</Text>
            <Ionicons name={serverOpen ? 'chevron-up' : 'chevron-down'} size={14} color={colors.inkMuted} />
          </Pressable>
          {serverOpen && (
            <View style={styles.serverBox}>
              <TextInput
                value={server}
                onChangeText={setServer}
                placeholder="http://192.168.29.75:8000"
                placeholderTextColor={colors.inkFaint}
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                style={styles.input}
              />
              <Text style={styles.help}>Only change this if the store gives you a new address. Saved when you sign in.</Text>
            </View>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.yellow },
  scroll: { flexGrow: 1, padding: 20, justifyContent: 'center' },
  hero: { alignItems: 'center', marginBottom: 28 },
  logo: {
    width: 72,
    height: 72,
    borderRadius: 20,
    backgroundColor: colors.ink,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 14,
  },
  logoText: { color: colors.yellow, fontSize: 28, fontWeight: '900' },
  title: { fontSize: 28, fontWeight: '900', color: colors.ink, letterSpacing: -0.4 },
  subtitle: { marginTop: 6, fontSize: 14, color: '#3D3200', textAlign: 'center' },
  form: { backgroundColor: colors.card, borderRadius: radius.xl, padding: 20, ...shadow },
  label: { fontSize: 12, fontWeight: '700', color: colors.inkMuted, marginBottom: 6, letterSpacing: 0.3 },
  input: {
    height: 48,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.sm,
    paddingHorizontal: 14,
    fontSize: 16,
    color: colors.ink,
    backgroundColor: colors.card,
  },
  passwordRow: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.sm,
  },
  eye: { paddingHorizontal: 12 },
  error: { marginTop: 12, color: colors.danger, fontSize: 13, fontWeight: '600' },
  button: {
    marginTop: 20,
    height: 50,
    borderRadius: radius.sm,
    backgroundColor: colors.brand,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  help: { marginTop: 12, fontSize: 12, color: colors.inkMuted, textAlign: 'center' },
  serverToggle: { marginTop: 24, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  serverToggleText: { fontSize: 12, color: colors.inkMuted },
  serverBox: { marginTop: 12 },
});
