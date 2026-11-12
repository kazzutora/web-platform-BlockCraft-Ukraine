import { Inter, JetBrains_Mono, Unbounded } from "next/font/google";

/** Headings and the logo: a wide geometric grotesque that hints at blocks. */
export const display = Unbounded({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "600"],
  variable: "--font-unbounded",
  display: "swap",
});

/** Body text and UI. */
export const sans = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});

/** Versions, addresses, online counts, hashes. */
export const mono = JetBrains_Mono({
  subsets: ["latin", "cyrillic"],
  weight: ["400", "500"],
  variable: "--font-jetbrains",
  display: "swap",
});
