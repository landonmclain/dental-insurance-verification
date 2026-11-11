"use client";

// ThemeToggle — cycles light -> dark -> system (mirrors paf-ui). Uses
// lucide-react icons (Sun/Moon/Monitor); this app has no shadcn Button, so
// the plain button keeps the prior styling.

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme, type Theme } from "./use-theme";

const ORDER: Theme[] = ["light", "dark", "system"];

const ICONS: Record<Theme, React.ReactNode> = {
  light: <Sun className="h-4 w-4" />,
  dark: <Moon className="h-4 w-4" />,
  system: <Monitor className="h-4 w-4" />,
};

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  const cycle = () => {
    const i = ORDER.indexOf(theme);
    setTheme(ORDER[(i + 1) % ORDER.length]);
  };

  return (
    <button
      type="button"
      aria-label={`Theme: ${theme}`}
      title={`Theme: ${theme} (click to cycle)`}
      onClick={cycle}
      className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:border-blue-300 hover:text-blue-600 dark:border-neutral-700 dark:text-neutral-400 dark:hover:border-blue-500 dark:hover:text-blue-400"
    >
      {ICONS[theme]}
    </button>
  );
}
