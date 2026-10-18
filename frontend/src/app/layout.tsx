import type { Metadata } from "next";
import { Suspense } from "react";

import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import { MobileTabBar } from "@/components/layout/MobileTabBar";
import { QueryProvider } from "@/components/layout/QueryProvider";
import { TabBarLinks } from "@/components/layout/TabBarLinks";
import { ThemeProvider } from "@/components/layout/ThemeProvider";
import { ToastProvider } from "@/components/ui/ToastProvider";
import { AuthPromptProvider } from "@/features/auth/AuthPromptProvider";
import { cn } from "@/lib/cn";
import "@/styles/globals.css";

import { sans, serif } from "./fonts";

const copy = {
  title: "BlockCraft Ukraine",
  description: "Моди, скіни й сервери Minecraft українською.",
  skip: "Перейти до вмісту",
};

export const metadata: Metadata = {
  title: { default: copy.title, template: `%s · ${copy.title}` },
  description: copy.description,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="uk"
      suppressHydrationWarning
      className={cn(serif.variable, sans.variable, "h-full antialiased")}
    >
      <body className="flex min-h-full flex-col">
        <ThemeProvider>
          <QueryProvider>
            <ToastProvider>
              <AuthPromptProvider>
                {/* Modals mark their siblings aria-hidden; marking this always-hydrated wrapper
                    instead of the tab bar (a later Suspense boundary) keeps hydration clean */}
                <div className="flex flex-1 flex-col">
                  <a
                    href="#main"
                    className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-primary-bg focus:px-4 focus:py-2 focus:text-primary-fg"
                  >
                    {copy.skip}
                  </a>
                  <Header />
                  <main id="main" className="flex flex-1 flex-col">
                    {children}
                  </main>
                  <Footer />
                  <Suspense fallback={<TabBarLinks />}>
                    <MobileTabBar />
                  </Suspense>
                </div>
              </AuthPromptProvider>
            </ToastProvider>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
