import * as Updates from 'expo-updates';
import { useEffect } from 'react';
import { Platform } from 'react-native';

/** On launch, fetch any app update published with `eas update` and switch to it right away,
 *  rather than waiting for the next launch (the built-in ON_LOAD behaviour). Installed
 *  builds only: the APIs reject in development and Expo Go, and the web preview has none.
 *  Offline or a server hiccup just means the current version keeps running. */
export function useAppUpdates() {
  useEffect(() => {
    if (__DEV__ || Platform.OS === 'web' || !Updates.isEnabled) return;
    (async () => {
      try {
        const update = await Updates.checkForUpdateAsync();
        if (!update.isAvailable) return;
        await Updates.fetchUpdateAsync();
        await Updates.reloadAsync();
      } catch {
        // Keep running the version already on the phone.
      }
    })();
  }, []);
}
