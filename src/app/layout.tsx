import type { Metadata, Viewport } from "next";
import { Inter_Tight, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import "./print.css";

const sans = Inter_Tight({ variable: "--font-inter-tight", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], weight: ["400", "600"] });

export const metadata: Metadata = {
  title: "SpectraSense · From enquiry to first experiment",
  description: "A first technical assessment assistant for AFS in-line spectroscopy experts.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, viewportFit: "cover" };

// Applies the saved theme before first paint, so dark mode does not flash light on load.
const prePaint = `try{if(localStorage.getItem("theme")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: prePaint }} />
      </head>
      <body className={`${sans.variable} ${serif.variable} antialiased`}>{children}</body>
    </html>
  );
}
