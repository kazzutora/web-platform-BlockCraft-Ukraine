import type { Metadata } from "next";
import "./globals.css";

const copy = {
  title: "BlockCraft Ukraine",
  description: "Моди, скіни й сервери Minecraft українською.",
};

export const metadata: Metadata = {
  title: copy.title,
  description: copy.description,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="uk" className="h-full antialiased">
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}
