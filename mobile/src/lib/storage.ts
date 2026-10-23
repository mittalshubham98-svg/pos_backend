import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/** Encrypted on-device storage on Android/iOS; plain localStorage on web (SecureStore has
 *  no web implementation), which is only used for previewing the app in a browser. */
export const storage = {
  get: (key: string): Promise<string | null> =>
    Platform.OS === 'web' ? Promise.resolve(globalThis.localStorage?.getItem(key) ?? null) : SecureStore.getItemAsync(key),

  set: (key: string, value: string): Promise<void> =>
    Platform.OS === 'web' ? Promise.resolve(globalThis.localStorage?.setItem(key, value)) : SecureStore.setItemAsync(key, value),

  remove: (key: string): Promise<void> =>
    Platform.OS === 'web' ? Promise.resolve(globalThis.localStorage?.removeItem(key)) : SecureStore.deleteItemAsync(key),
};
