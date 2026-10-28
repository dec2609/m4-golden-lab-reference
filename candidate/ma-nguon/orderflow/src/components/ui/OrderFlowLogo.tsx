import type { ImgHTMLAttributes } from "react";
import { cn } from "../../lib/utils";
import { useAppearance } from "../../lib/appearance";

import primaryCleanLogo from "../../assets/brand/orderflow-primary-clean.png";
import primaryClean2Logo from "../../assets/brand/orderflow-primary-clean-2.png";
import primaryLogo from "../../assets/brand/orderflow-primary.png";
import markLogo from "../../assets/brand/orderflow-mark.png";
import compactLogo from "../../assets/brand/orderflow-compact.png";
import wordmarkLogo from "../../assets/brand/orderflow-wordmark.png";
import appMarkLogo from "../../assets/brand/orderflow-app-mark.png";
import faviconLogo from "../../assets/brand/orderflow-favicon.png";
import monoDarkLogo from "../../assets/brand/orderflow-monochrome-dark.png";
import monoLightLogo from "../../assets/brand/orderflow-monochrome-light.png";

export type LogoVariant =
  | "auto"
  | "primary"
  | "clean"
  | "clean-2"
  | "mark"
  | "compact"
  | "wordmark"
  | "app-mark"
  | "favicon"
  | "monochrome-dark"
  | "monochrome-light";

export type LogoContext =
  | "sidebar-expanded"
  | "sidebar-compact"
  | "mobile-header"
  | "presentational"
  | "app-icon";

export interface OrderFlowLogoProps
  extends Omit<ImgHTMLAttributes<HTMLImageElement>, "src"> {
  variant?: LogoVariant;
  context?: LogoContext;
  themeOverride?: "light" | "dark";
}

const logoSources: Record<Exclude<LogoVariant, "auto">, string> = {
  primary: primaryLogo,
  clean: primaryCleanLogo,
  "clean-2": primaryClean2Logo,
  mark: markLogo,
  compact: compactLogo,
  wordmark: wordmarkLogo,
  "app-mark": appMarkLogo,
  favicon: faviconLogo,
  "monochrome-dark": monoDarkLogo,
  "monochrome-light": monoLightLogo,
};

const defaultAlts: Record<Exclude<LogoVariant, "auto">, string> = {
  primary: "OrderFlow — Every Release Has A Trace",
  clean: "OrderFlow",
  "clean-2": "OrderFlow",
  mark: "OrderFlow Mark",
  compact: "OrderFlow",
  wordmark: "OrderFlow",
  "app-mark": "OrderFlow App",
  favicon: "OrderFlow Favicon",
  "monochrome-dark": "OrderFlow",
  "monochrome-light": "OrderFlow",
};

export default function OrderFlowLogo({
  variant = "auto",
  context,
  themeOverride,
  alt,
  className,
  ...props
}: OrderFlowLogoProps) {
  const { resolvedTheme } = useAppearance();
  const currentTheme = themeOverride ?? resolvedTheme;
  const isDark = currentTheme === "dark";

  // Resolve effective variant based on variant, context, and theme
  let effectiveVariant: Exclude<LogoVariant, "auto">;

  if (variant !== "auto") {
    effectiveVariant = variant;
  } else if (context === "sidebar-compact") {
    effectiveVariant = "mark";
  } else if (context === "presentational") {
    effectiveVariant = "primary";
  } else if (context === "app-icon") {
    effectiveVariant = "app-mark";
  } else {
    // Default, sidebar-expanded, mobile-header:
    // Light -> orderflow-primary-clean.png
    // Dark -> orderflow-primary-clean-2.png
    effectiveVariant = isDark ? "clean-2" : "clean";
  }

  const src =
    logoSources[effectiveVariant] ||
    (isDark ? primaryClean2Logo : primaryCleanLogo);
  const resolvedAlt = alt ?? defaultAlts[effectiveVariant] ?? "OrderFlow";

  return (
    <img
      src={src}
      alt={resolvedAlt}
      className={cn("object-contain select-none shrink-0", className)}
      draggable={false}
      {...props}
    />
  );
}


