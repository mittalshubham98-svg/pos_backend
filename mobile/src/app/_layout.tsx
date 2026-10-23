import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { colors } from '@/lib/theme';
import { useAppUpdates } from '@/lib/useAppUpdates';
import { AuthProvider } from '@/state/auth';
import { CartProvider } from '@/state/cart';

export default function RootLayout() {
  useAppUpdates();
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <CartProvider>
          <StatusBar style="dark" />
          <Stack screenOptions={{ contentStyle: { backgroundColor: colors.bg } }}>
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="login" options={{ headerShown: false }} />
            <Stack.Screen
              name="regulars"
              options={{ title: 'Your regular items', headerTitleStyle: { fontWeight: '800' } }}
            />
            <Stack.Screen
              name="checkout"
              options={{
                presentation: 'modal',
                title: 'Checkout',
                headerTitleStyle: { fontWeight: '800' },
              }}
            />
          </Stack>
        </CartProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
