import type { Metadata } from "next";
import { notFound } from "next/navigation";

export const metadata: Metadata = {
  title: "Дизайн-система",
  robots: { index: false, follow: false },
};

/** Developer pages exist only in `next dev`. */
export default function DevLayout({ children }: LayoutProps<"/dev">) {
  if (process.env.NODE_ENV === "production") {
    notFound();
  }
  return children;
}
