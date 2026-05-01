/**
 * app/layout.tsx
 * Root layout — sets global font, dark background, metadata.
 */
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

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
    <html lang="fr" className="dark">
      <body className={`${inter.className} bg-[#0f0f1a] antialiased`}>
        {children}
      </body>
    </html>
  );
}
