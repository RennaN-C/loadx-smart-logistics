import { useSyncExternalStore } from "react";

export type Appearance = "light" | "dark" | "system";
declare global {
  interface Window {
    loadxTheme: {
      preference: () => Appearance;
      dark: () => boolean;
      set: (value: Appearance) => void;
      subscribe: (listener: () => void) => () => void;
    };
  }
}

export function useAppearance() {
  const preference = useSyncExternalStore(window.loadxTheme.subscribe, window.loadxTheme.preference);
  return { preference, setPreference: window.loadxTheme.set };
}

export function useDarkAppearance() {
  return useSyncExternalStore(window.loadxTheme.subscribe, window.loadxTheme.dark);
}
