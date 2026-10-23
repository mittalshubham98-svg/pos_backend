import { Ionicons } from '@expo/vector-icons';
import { Image } from 'expo-image';
import { router } from 'expo-router';
import { useState } from 'react';
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
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { api, Order, upiQrUrl } from '@/lib/api';
import { rupees } from '@/lib/format';
import { colors, radius, shadow } from '@/lib/theme';
import { useAuth } from '@/state/auth';
import { useCart } from '@/state/cart';

type PayMode = 'upi' | 'account';

export default function CheckoutScreen() {
  const auth = useAuth();
  const cart = useCart();
  const insets = useSafeAreaInsets();
  const [unlisted, setUnlisted] = useState('');
  const [payMode, setPayMode] = useState<PayMode>('upi');
  const [utr, setUtr] = useState('');
  const [qrFailed, setQrFailed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [placed, setPlaced] = useState<Order | null>(null);

  const utrDigits = utr.replace(/\D/g, '');
  const hasSomething = cart.lines.length > 0 || unlisted.trim().length > 0;
  const utrOk = payMode === 'account' || utrDigits.length === 12;
  const canPlace = hasSomething && utrOk && !busy;

  async function placeOrder() {
    if (!canPlace || !auth.session) return;
    setBusy(true);
    setError(null);
    try {
      const order = await api.placeOrder(auth.apiUrl, auth.session.token, {
        lines: cart.toOrderLines(),
        unlisted_text: unlisted.trim(),
        utr: payMode === 'upi' ? utrDigits : null,
      });
      cart.clear();
      setPlaced(order);
    } catch (err) {
      auth.handleAuthError(err);
      setError(err instanceof Error ? err.message : 'Could not place the order');
    } finally {
      setBusy(false);
    }
  }

  if (placed) {
    return (
      <View style={[styles.done, { paddingBottom: insets.bottom + 24 }]}>
        <View style={styles.doneIcon}>
          <Ionicons name="checkmark" size={44} color="#fff" />
        </View>
        <Text style={styles.doneTitle}>Order placed!</Text>
        <Text style={styles.doneSub}>{placed.po_number}</Text>
        <View style={styles.doneCard}>
          <DoneRow label="Items" value={String(placed.lines.length)} />
          {placed.unlisted_text ? <DoneRow label="Unlisted request" value="Sent to store" /> : null}
          <DoneRow label="Order value" value={rupees(placed.totals.grand_total)} />
          <DoneRow label="Payment" value={placed.utr ? `UPI · UTR ${placed.utr}` : 'Added to your account'} />
        </View>
        <Text style={styles.doneNote}>The store will confirm quantities and send your GST invoice.</Text>
        <Pressable
          style={styles.primary}
          onPress={() => {
            router.back();
            router.navigate('/orders');
          }}
        >
          <Text style={styles.primaryText}>View my orders</Text>
        </Pressable>
        <Pressable onPress={() => router.back()} hitSlop={8}>
          <Text style={styles.link}>Continue shopping</Text>
        </Pressable>
      </View>
    );
  }

  const roundedTotal = Math.round(cart.total);

  return (
    <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined} keyboardVerticalOffset={80}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Section title="Order summary">
          {cart.lines.length === 0 ? (
            <Text style={styles.muted}>No catalogue items — you can still send an unlisted list below.</Text>
          ) : (
            <>
              <SummaryRow label={`${cart.itemCount} item${cart.itemCount === 1 ? '' : 's'} (MRP ${rupees(cart.mrpTotal)})`} value={rupees(cart.total)} />
              {cart.mrpTotal - cart.total >= 1 && (
                <SummaryRow label="You save" value={`− ${rupees(cart.mrpTotal - cart.total)}`} green />
              )}
              <View style={styles.divider} />
              <SummaryRow label="Amount to pay" value={rupees(roundedTotal)} bold />
              <Text style={styles.hint}>Estimate incl. GST — final amount is on your tax invoice.</Text>
            </>
          )}
        </Section>

        <Section title="Anything not in the list?">
          <TextInput
            value={unlisted}
            onChangeText={setUnlisted}
            placeholder={'One item per line — brand, size, quantity\ne.g. Kabuli chana 1kg — 5 packets'}
            placeholderTextColor={colors.inkFaint}
            multiline
            textAlignVertical="top"
            style={[styles.input, styles.textarea]}
          />
        </Section>

        <Section title="Payment">
          <View style={styles.segment}>
            <SegmentButton active={payMode === 'upi'} label="Pay now by UPI" icon="qr-code-outline" onPress={() => setPayMode('upi')} />
            <SegmentButton active={payMode === 'account'} label="On account" icon="wallet-outline" onPress={() => setPayMode('account')} />
          </View>

          {payMode === 'upi' ? (
            <>
              <View style={styles.qrBox}>
                {qrFailed ? (
                  <View style={styles.qrMissing}>
                    <Ionicons name="qr-code-outline" size={36} color={colors.inkFaint} />
                    <Text style={styles.muted}>The store hasn't uploaded its UPI QR yet. Choose "On account" or ask the store.</Text>
                  </View>
                ) : (
                  <Image
                    source={{ uri: upiQrUrl(auth.apiUrl) }}
                    style={styles.qr}
                    contentFit="contain"
                    cachePolicy="none"
                    onError={() => setQrFailed(true)}
                    accessibilityLabel="Store UPI QR code"
                  />
                )}
                {roundedTotal > 0 && <Text style={styles.qrAmount}>Pay {rupees(roundedTotal)}</Text>}
                <Text style={styles.muted}>Scan with any UPI app, pay, then enter the 12-digit UTR / reference number below.</Text>
              </View>
              <Text style={styles.label}>UTR / UPI reference number</Text>
              <TextInput
                value={utr}
                onChangeText={(t) => setUtr(t.replace(/[^\d ]/g, '').slice(0, 15))}
                placeholder="12-digit number from your UPI app"
                placeholderTextColor={colors.inkFaint}
                keyboardType="number-pad"
                style={styles.input}
              />
              {utrDigits.length > 0 && utrDigits.length !== 12 && (
                <Text style={styles.warn}>UTR should be 12 digits ({utrDigits.length} entered).</Text>
              )}
            </>
          ) : (
            <Text style={styles.muted}>The order value is added to your balance with the store. Pay later as agreed.</Text>
          )}
        </Section>

        {error && <Text style={styles.error}>{error}</Text>}
      </ScrollView>

      <View style={[styles.footer, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        <View style={{ flex: 1 }}>
          <Text style={styles.footerTotal}>{rupees(roundedTotal)}</Text>
          <Text style={styles.footerSub}>{payMode === 'upi' ? 'Paid by UPI' : 'On account'}</Text>
        </View>
        <Pressable
          onPress={placeOrder}
          disabled={!canPlace}
          style={({ pressed }) => [styles.placeBtn, !canPlace && { opacity: 0.45 }, pressed && { opacity: 0.85 }]}
          accessibilityRole="button"
        >
          {busy ? <ActivityIndicator color="#fff" /> : <Text style={styles.placeText}>Place order</Text>}
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  );
}

function SummaryRow({ label, value, bold, green }: { label: string; value: string; bold?: boolean; green?: boolean }) {
  return (
    <View style={styles.summaryRow}>
      <Text style={[styles.summaryLabel, bold && styles.bold]} numberOfLines={1}>
        {label}
      </Text>
      <Text style={[styles.summaryValue, bold && styles.bold, green && { color: colors.green }]}>{value}</Text>
    </View>
  );
}

function SegmentButton({
  active,
  label,
  icon,
  onPress,
}: {
  active: boolean;
  label: string;
  icon: keyof typeof Ionicons.glyphMap;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={[styles.segBtn, active && styles.segBtnActive]}
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
    >
      <Ionicons name={icon} size={16} color={active ? '#fff' : colors.ink} />
      <Text style={[styles.segText, active && { color: '#fff' }]}>{label}</Text>
    </Pressable>
  );
}

function DoneRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.summaryRow}>
      <Text style={styles.summaryLabel}>{label}</Text>
      <Text style={[styles.summaryValue, { flexShrink: 1, textAlign: 'right' }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: 12, gap: 12, paddingBottom: 24 },
  section: { backgroundColor: colors.card, borderRadius: radius.md, padding: 16, gap: 10, ...shadow },
  sectionTitle: { fontSize: 15, fontWeight: '800', color: colors.ink },
  muted: { fontSize: 13, color: colors.inkMuted, textAlign: 'center' },
  hint: { fontSize: 11, color: colors.inkFaint },
  summaryRow: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  summaryLabel: { flexShrink: 1, fontSize: 13, color: colors.inkMuted },
  summaryValue: { fontSize: 13, fontWeight: '600', color: colors.ink },
  bold: { fontSize: 16, fontWeight: '900', color: colors.ink },
  divider: { height: StyleSheet.hairlineWidth, backgroundColor: colors.line },
  label: { fontSize: 12, fontWeight: '700', color: colors.inkMuted },
  input: {
    minHeight: 48,
    borderWidth: 1,
    borderColor: colors.line,
    borderRadius: radius.sm,
    paddingHorizontal: 14,
    fontSize: 16,
    color: colors.ink,
  },
  textarea: { minHeight: 96, paddingTop: 12, fontSize: 14 },
  segment: { flexDirection: 'row', gap: 8 },
  segBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    height: 42,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.line,
  },
  segBtnActive: { backgroundColor: colors.ink, borderColor: colors.ink },
  segText: { fontSize: 13, fontWeight: '700', color: colors.ink },
  qrBox: { alignItems: 'center', gap: 8, paddingVertical: 4 },
  qr: { width: 220, height: 220, borderRadius: radius.sm, backgroundColor: '#fff' },
  qrMissing: { width: 220, height: 160, alignItems: 'center', justifyContent: 'center', gap: 8 },
  qrAmount: { fontSize: 18, fontWeight: '900', color: colors.ink },
  warn: { fontSize: 12, color: colors.amber, fontWeight: '600' },
  error: { color: colors.brandDark, fontWeight: '700', textAlign: 'center', paddingHorizontal: 12 },
  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingTop: 12,
    backgroundColor: colors.card,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.line,
  },
  footerTotal: { fontSize: 18, fontWeight: '900', color: colors.ink },
  footerSub: { fontSize: 11, color: colors.inkMuted },
  placeBtn: {
    backgroundColor: colors.green,
    borderRadius: radius.sm,
    height: 50,
    paddingHorizontal: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeText: { color: '#fff', fontSize: 16, fontWeight: '800' },
  done: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 10 },
  doneIcon: {
    width: 84,
    height: 84,
    borderRadius: 42,
    backgroundColor: colors.green,
    alignItems: 'center',
    justifyContent: 'center',
  },
  doneTitle: { fontSize: 24, fontWeight: '900', color: colors.ink, marginTop: 8 },
  doneSub: { fontSize: 14, color: colors.inkMuted, fontWeight: '700' },
  doneCard: { alignSelf: 'stretch', backgroundColor: colors.card, borderRadius: radius.md, padding: 16, gap: 8, marginTop: 8, ...shadow },
  doneNote: { fontSize: 12, color: colors.inkMuted, textAlign: 'center', marginTop: 4 },
  primary: { marginTop: 10, backgroundColor: colors.brand, borderRadius: radius.sm, paddingHorizontal: 24, paddingVertical: 14 },
  primaryText: { color: '#fff', fontWeight: '800', fontSize: 15 },
  link: { marginTop: 4, color: colors.brand, fontWeight: '700' },
});
