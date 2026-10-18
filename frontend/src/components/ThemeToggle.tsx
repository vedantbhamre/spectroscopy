"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

// Switches between the light (default) and dark palettes in globals.css and remembers the choice.
export function ThemeToggle({ inverse = false }: { inverse?: boolean }) {
  const [dark, setDark] = useState(false);

  useEffect(() => {
    setDark(document.documentElement.dataset.theme === "dark");
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    if (next) document.documentElement.dataset.theme = "dark";
    else delete document.documentElement.dataset.theme;
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      // storage unavailable (private mode): the choice lasts for this page only
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={dark ? "Switch to light theme" : "Switch to dark theme"}
      title={dark ? "Light theme" : "Dark theme"}
      className={`ml-1 flex h-8 w-8 items-center justify-center rounded-md border ${inverse ? "border-white/25 bg-white/5 text-white/85 hover:bg-white/15 hover:text-white" : "border-line text-ink-2 hover:bg-panel hover:text-ink"}`}
    >
      {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  );
}
