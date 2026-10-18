import { Cormorant_Garamond, Inter } from "next/font/google";

/** Headings. */
export const serif = Cormorant_Garamond({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "600"],
  variable: "--font-cormorant",
  display: "swap",
});

/** Body text and UI. */
export const sans = Inter({
  subsets: ["latin", "cyrillic"],
  variable: "--font-inter",
  display: "swap",
});
