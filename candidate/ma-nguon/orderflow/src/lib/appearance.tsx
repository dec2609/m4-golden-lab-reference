import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Theme = "light" | "dark" | "system";
export type ResolvedTheme = "light" | "dark";
export type SidebarMode = "expanded" | "compact";

export interface ThemeTransitionOrigin {
  clientX?: number;
  clientY?: number;
}

export interface AppearanceContextValue {
  theme: Theme;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: Theme, origin?: ThemeTransitionOrigin) => void;
  sidebarMode: SidebarMode;
  setSidebarMode: (mode: SidebarMode) => void;
  toggleSidebarMode: () => void;
}

const STORAGE_KEY_THEME = "orderflow-theme";
const STORAGE_KEY_SIDEBAR = "orderflow-sidebar";

const AppearanceContext = createContext<AppearanceContextValue | null>(null);

function getInitialTheme(): Theme {
  try {
    if (typeof window !== "undefined") {
      const q = new URLSearchParams(window.location.search).get("theme");
      if (q === "light" || q === "dark" || q === "system") {
        return q;
      }
    }
    const saved = localStorage.getItem(STORAGE_KEY_THEME);
    if (saved === "light" || saved === "dark" || saved === "system") {
      return saved;
    }
  } catch {
    // ignore localStorage access errors
  }
  return "system";
}

function getInitialSidebar(): SidebarMode {
  try {
    if (typeof window !== "undefined") {
      const q = new URLSearchParams(window.location.search).get("sidebar");
      if (q === "expanded" || q === "compact") {
        return q;
      }
    }
    const saved = localStorage.getItem(STORAGE_KEY_SIDEBAR);
    if (saved === "expanded" || saved === "compact") {
      return saved;
    }
  } catch {
    // ignore localStorage access errors
  }
  return "expanded";
}

function getSystemPreference(): ResolvedTheme {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function AppearanceProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(getInitialTheme);
  const [systemDark, setSystemDark] = useState<boolean>(() => {
    if (typeof window === "undefined") return false;
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });
  const [sidebarMode, setSidebarModeState] = useState<SidebarMode>(getInitialSidebar);

  // Listen to OS system color scheme changes
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (e: MediaQueryListEvent) => {
      setSystemDark(e.matches);
    };
    media.addEventListener("change", handler);
    return () => media.removeEventListener("change", handler);
  }, []);

  const resolvedTheme: ResolvedTheme =
    theme === "system" ? (systemDark ? "dark" : "light") : theme;

  // Apply theme to DOM and persist
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-theme", resolvedTheme);
    if (resolvedTheme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }

    try {
      localStorage.setItem(STORAGE_KEY_THEME, theme);
    } catch {
      // ignore storage write errors
    }
  }, [theme, resolvedTheme]);

  // Apply sidebar mode to CSS variable and persist
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute("data-sidebar", sidebarMode);
    root.style.setProperty(
      "--sidebar-width",
      sidebarMode === "compact" ? "64px" : "240px",
    );

    try {
      localStorage.setItem(STORAGE_KEY_SIDEBAR, sidebarMode);
    } catch {
      // ignore storage write errors
    }
  }, [sidebarMode]);

// Soft blurred SVG mask data URI (feathered circular reveal)
const SOFT_MASK_SVG = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><filter id="feather" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="3"/></filter></defs><circle cx="50" cy="50" r="42" fill="white" filter="url(#feather)"/></svg>`;
const SOFT_MASK_URI = `data:image/svg+xml,${encodeURIComponent(SOFT_MASK_SVG)}`;

  const setTheme = useCallback(
    (nextTheme: Theme, origin?: ThemeTransitionOrigin) => {
      if (nextTheme === theme) return;

      const nextResolved: ResolvedTheme =
        nextTheme === "system" ? (systemDark ? "dark" : "light") : nextTheme;

      // If resolved visual theme does not change
      if (nextResolved === resolvedTheme) {
        setThemeState(nextTheme);
        return;
      }

      const isReducedMotion =
        typeof window !== "undefined" &&
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      const doc = typeof document !== "undefined" ? document : null;
      const root = doc ? doc.documentElement : null;

      // View Transition API (Soft blurred SVG mask reveal expanding from origin)
      if (
        doc &&
        root &&
        "startViewTransition" in doc &&
        !isReducedMotion
      ) {
        let x = window.innerWidth / 2;
        let y = window.innerHeight / 2;

        if (origin && typeof origin.clientX === "number" && typeof origin.clientY === "number") {
          x = origin.clientX;
          y = origin.clientY;
        } else if (doc.activeElement) {
          const rect = doc.activeElement.getBoundingClientRect();
          if (rect.width > 0 && rect.height > 0) {
            x = rect.left + rect.width / 2;
            y = rect.top + rect.height / 2;
          }
        }

        const maxDist = Math.hypot(
          Math.max(x, window.innerWidth - x),
          Math.max(y, window.innerHeight - y)
        );
        // The solid white core of the feathered SVG (r=42, stdDev=3) covers ~0.72 of half-size.
        // Scale endRadius so the solid core covers all corners before the transition ends.
        const endRadius = Math.ceil(maxDist / 0.72);
        const diameter = endRadius * 2;

        root.style.setProperty("--theme-reveal-x", `${x}px`);
        root.style.setProperty("--theme-reveal-y", `${y}px`);

        try {
          const transition = (doc as Document & {
            startViewTransition: (cb: () => void) => {
              ready: Promise<void>;
              finished: Promise<void>;
            };
          }).startViewTransition(() => {
            setThemeState(nextTheme);
            root.setAttribute("data-theme", nextResolved);
            if (nextResolved === "dark") {
              root.classList.add("dark");
            } else {
              root.classList.remove("dark");
            }
            try {
              localStorage.setItem(STORAGE_KEY_THEME, nextTheme);
            } catch {}
          });

          transition.ready
            .then(() => {
              try {
                root.animate(
                  {
                    maskImage: [`url("${SOFT_MASK_URI}")`, `url("${SOFT_MASK_URI}")`],
                    webkitMaskImage: [`url("${SOFT_MASK_URI}")`, `url("${SOFT_MASK_URI}")`],
                    maskRepeat: ["no-repeat", "no-repeat"],
                    webkitMaskRepeat: ["no-repeat", "no-repeat"],
                    maskPosition: [
                      `${x}px ${y}px`,
                      `${x - endRadius}px ${y - endRadius}px`,
                    ],
                    webkitMaskPosition: [
                      `${x}px ${y}px`,
                      `${x - endRadius}px ${y - endRadius}px`,
                    ],
                    maskSize: ["0px 0px", `${diameter}px ${diameter}px`],
                    webkitMaskSize: ["0px 0px", `${diameter}px ${diameter}px`],
                  },
                  {
                    duration: 400,
                    easing: "cubic-bezier(0.16, 1, 0.3, 1)",
                    pseudoElement: "::view-transition-new(root)",
                  }
                );
              } catch {
                // Graceful fallback to clip-path if mask animation is unsupported
                root.animate(
                  {
                    clipPath: [
                      `circle(0px at ${x}px ${y}px)`,
                      `circle(${endRadius}px at ${x}px ${y}px)`,
                    ],
                  },
                  {
                    duration: 400,
                    easing: "cubic-bezier(0.16, 1, 0.3, 1)",
                    pseudoElement: "::view-transition-new(root)",
                  }
                );
              }
            })
            .catch(() => {
              // Ignore abort errors from rapid clicks
            });
          return;
        } catch {
          // Fall through to fallback
        }
      }

      // Browser Fallback (CSS Color Morphing)
      if (root && !isReducedMotion) {
        root.classList.add("theme-morphing");
        setThemeState(nextTheme);
        root.setAttribute("data-theme", nextResolved);
        if (nextResolved === "dark") {
          root.classList.add("dark");
        } else {
          root.classList.remove("dark");
        }
        try {
          localStorage.setItem(STORAGE_KEY_THEME, nextTheme);
        } catch {}

        setTimeout(() => {
          root.classList.remove("theme-morphing");
        }, 400);
      } else {
        // Reduced motion or SSR: Instant update
        setThemeState(nextTheme);
        if (root) {
          root.setAttribute("data-theme", nextResolved);
          if (nextResolved === "dark") {
            root.classList.add("dark");
          } else {
            root.classList.remove("dark");
          }
        }
        try {
          localStorage.setItem(STORAGE_KEY_THEME, nextTheme);
        } catch {}
      }
    },
    [theme, resolvedTheme, systemDark]
  );

  const setSidebarMode = useCallback((nextMode: SidebarMode) => {
    setSidebarModeState(nextMode);
  }, []);

  const toggleSidebarMode = useCallback(() => {
    setSidebarModeState((prev) => (prev === "expanded" ? "compact" : "expanded"));
  }, []);

  return (
    <AppearanceContext.Provider
      value={{
        theme,
        resolvedTheme,
        setTheme,
        sidebarMode,
        setSidebarMode,
        toggleSidebarMode,
      }}
    >
      {children}
    </AppearanceContext.Provider>
  );
}

export function useAppearance(): AppearanceContextValue {
  const context = useContext(AppearanceContext);
  if (!context) {
    // Graceful fallback for components rendered outside AppearanceProvider
    return {
      theme: "system",
      resolvedTheme: getSystemPreference(),
      setTheme: () => {},
      sidebarMode: "expanded",
      setSidebarMode: () => {},
      toggleSidebarMode: () => {},
    };
  }
  return context;
}
