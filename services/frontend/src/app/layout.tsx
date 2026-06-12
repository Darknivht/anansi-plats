import type { Metadata, Viewport } from "next";
import { DM_Sans, Inter, DM_Mono } from "next/font/google";
import "./globals.css";

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  weight: ["400", "500", "600", "700", "800"],
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600"],
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  variable: "--font-dm-mono",
  weight: ["400", "500"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    template: "%s | Anansi",
    default: "Anansi — Your AI. Your Life. Your OS.",
  },
  description:
    "Anansi is a Personal AI Operating System with a true Second Brain — your AI manages your digital life through a beautiful web interface, with natural conversation on WhatsApp and voice.",
  keywords: [
    "AI",
    "Second Brain",
    "personal AI",
    "productivity",
    "agent",
    "automation",
    "knowledge management",
    "Obsidian",
    "Zettelkasten",
  ],
  authors: [{ name: "Anansi" }],
  openGraph: {
    type: "website",
    locale: "en_US",
    siteName: "Anansi",
    title: "Anansi — Your AI. Your Life. Your OS.",
    description:
      "A Personal AI Operating System with a true Second Brain that learns, links, and grows with you.",
  },
  twitter: {
    card: "summary_large_image",
    title: "Anansi — Your AI. Your Life. Your OS.",
    description:
      "A Personal AI Operating System with a true Second Brain that learns, links, and grows with you.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0C0A09",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`dark ${dmSans.variable} ${inter.variable} ${dmMono.variable}`}
      suppressHydrationWarning
    >
      <body className="bg-[var(--color-bg-deepest)] text-[var(--color-text-primary)] antialiased">
        {children}
      </body>
    </html>
  );
}
