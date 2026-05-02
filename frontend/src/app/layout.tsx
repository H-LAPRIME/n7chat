/**
 * app/layout.tsx
 * Root layout — sets global font, dark background, metadata.
 */
import type { Metadata } from "next";
import { Inter, Playfair_Display } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap", variable: "--font-inter" });
const playfair = Playfair_Display({ subsets: ["latin"], display: "swap", variable: "--font-playfair" });

export const metadata: Metadata = {
  title: "n7chat — Plateforme Éducative IA",
  description:
    "Assistant éducatif intelligent avec orchestration multi-agents, recherche sémantique et accès basé sur les rôles.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className={`${inter.variable} ${playfair.variable} font-sans bg-background text-slate-900 antialiased`}>
        {children}
      </body>
    </html>
  );
}
