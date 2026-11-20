import { useSyncExternalStore } from "react";

import { Icon } from "./Icon";

type Theme = "auto" | "light" | "dark";
const KEY = "planner-theme";
const NEXT: Record<Theme, Theme> = { auto: "light", light: "dark", dark: "auto" };
const LABEL: Record<Theme, string> = { auto: "Thème automatique", light: "Thème clair", dark: "Thème sombre" };
const ICON = { auto: "auto", light: "sun", dark: "moon" } as const;

function read(): Theme {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" ? v : "auto";
  } catch {
    return "auto";
  }
}

// Store partagé : tous les boutons de thème restent synchronisés.
let current: Theme = typeof window === "undefined" ? "auto" : read();
const listeners = new Set<() => void>();

function apply(t: Theme) {
  current = t;
  const root = document.documentElement;
  if (t === "auto") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", t);
  try {
    localStorage.setItem(KEY, t);
  } catch { /* stockage indisponible : préférence non mémorisée */ }
  listeners.forEach((l) => l());
}
if (typeof document !== "undefined" && current !== "auto") document.documentElement.setAttribute("data-theme", current);

export function useTheme() {
  const theme = useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => { listeners.delete(cb); }; },
    () => current, () => "auto" as Theme);
  return { theme, cycle: () => apply(NEXT[current]) };
}

export function ThemeToggle({ variant = "icon" }: { variant?: "icon" | "tab" }) {
  const { theme, cycle } = useTheme();
  if (variant === "tab") {
    return (
      <button type="button" onClick={cycle} aria-label={`${LABEL[theme]} (changer)`}>
        <Icon name={ICON[theme]} /><span>Thème</span>
      </button>
    );
  }
  return (
    <button type="button" className="icon-btn theme-desktop" onClick={cycle} title={`${LABEL[theme]} — cliquer pour changer`}
            aria-label={`${LABEL[theme]} (changer)`}>
      <Icon name={ICON[theme]} />
    </button>
  );
}
