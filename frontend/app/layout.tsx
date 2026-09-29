import type { Metadata } from "next";
import { Geist, Geist_Mono, Newsreader } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
});

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const siteUrl = "https://deeptrace.mychatbot.codes";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "DeepTrace — Explainable AI Document Forensics",
  description:
    "Institutional document forensics, sub-pixel typography verification, and automated tamper detection for banking and regulatory compliance.",
  applicationName: "DeepTrace",
  authors: [{ name: "DeepTrace Forensics" }],
  keywords: [
    "document forensics",
    "explainable AI",
    "financial fraud detection",
    "sub-pixel typography",
    "tamper detection",
    "SBP compliance",
  ],
  icons: {
    icon: [
      { url: "/icon.png", sizes: "512x512", type: "image/png" },
      { url: "/favicon.ico", sizes: "any" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
  },
  openGraph: {
    title: "DeepTrace — Explainable AI Document Forensics",
    description:
      "Institutional document forensics, sub-pixel typography verification, and automated tamper detection.",
    url: siteUrl,
    siteName: "DeepTrace Forensics",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "DeepTrace — Explainable AI Document Forensics",
      },
    ],
    locale: "en_US",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "DeepTrace — Explainable AI Document Forensics",
    description:
      "Institutional document forensics, sub-pixel typography verification, and automated tamper detection.",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${newsreader.variable} ${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body
        suppressHydrationWarning
        className="min-h-full flex flex-col bg-paper-0 text-ink-900 selection:bg-forensic-red selection:text-white"
      >
        <ErrorBoundary>
          <AuthProvider>{children}</AuthProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
