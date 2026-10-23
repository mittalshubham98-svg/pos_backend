import { Pressable, StyleSheet, Text, View } from 'react-native';

import { colors, radius } from '@/lib/theme';

type Props = {
  qty: number;
  onAdd: () => void;
  onChange: (qty: number) => void;
  addLabel?: string;
  compact?: boolean;
};

/** Blinkit-style control: an outlined ADD button that turns into a filled − qty + stepper. */
export function QtyStepper({ qty, onAdd, onChange, addLabel = 'ADD', compact }: Props) {
  const height = compact ? 30 : 34;
  if (qty <= 0) {
    return (
      <Pressable
        onPress={onAdd}
        accessibilityRole="button"
        accessibilityLabel={addLabel}
        style={({ pressed }) => [styles.add, { height }, pressed && { opacity: 0.7 }]}
      >
        <Text style={styles.addText}>{addLabel}</Text>
      </Pressable>
    );
  }
  return (
    <View style={[styles.stepper, { height }]}>
      <Pressable onPress={() => onChange(qty - 1)} hitSlop={8} style={styles.btn} accessibilityLabel="Decrease quantity">
        <Text style={styles.btnText}>−</Text>
      </Pressable>
      <Text style={styles.qty}>{qty}</Text>
      <Pressable onPress={() => onChange(qty + 1)} hitSlop={8} style={styles.btn} accessibilityLabel="Increase quantity">
        <Text style={styles.btnText}>+</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  add: {
    minWidth: 76,
    paddingHorizontal: 12,
    borderRadius: radius.sm,
    borderWidth: 1.5,
    borderColor: colors.green,
    backgroundColor: colors.greenTint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addText: { color: colors.green, fontWeight: '800', fontSize: 13, letterSpacing: 0.5 },
  stepper: {
    minWidth: 76,
    borderRadius: radius.sm,
    backgroundColor: colors.green,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  btn: { paddingHorizontal: 10, height: '100%', justifyContent: 'center' },
  btnText: { color: '#fff', fontSize: 18, fontWeight: '800' },
  qty: { color: '#fff', fontWeight: '800', fontSize: 14, minWidth: 18, textAlign: 'center' },
});
