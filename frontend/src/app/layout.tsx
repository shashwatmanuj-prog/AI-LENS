import type { Metadata } from "next";
import { Mukta, Noto_Sans_Kannada } from "next/font/google";
import "./globals.css";
import { LanguageProvider } from "@/components/language-provider";
import { SiteHeader } from "@/components/site-header";

const mukta = Mukta({
  subsets: ["latin", "devanagari"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-mukta",
  display: "swap",
});

const kannada = Noto_Sans_Kannada({
  subsets: ["kannada"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-kannada",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CommunityLens AI",
  description: "Turn notices, circulars and posters into clear deadlines, checklists and verified facts. Powered by Gemma 4.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${mukta.variable} ${kannada.variable}`}>
      <body className="min-h-screen font-sans">
        <LanguageProvider>
          <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-card focus:px-3 focus:py-2">
            Skip to content
          </a>
          <SiteHeader />
          <main id="main" className="container pb-20 pt-8">
            {children}
          </main>
        </LanguageProvider>
      </body>
    </html>
  );
}
