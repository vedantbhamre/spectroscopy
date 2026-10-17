import type { Metadata } from "next";
import { Instrument_Sans, Source_Serif_4 } from "next/font/google";
import "./globals.css";
import "./print.css";

const sans = Instrument_Sans({ variable: "--font-instrument-sans", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const serif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"], weight: ["400", "600"] });

export const metadata: Metadata = {
  title: "SpectraSense AI · Art Fiber Systems",
  description: "A first technical assessment assistant for AFS in-line spectroscopy experts.",
};

// Applies the saved theme before first paint, so dark mode does not flash light on load.
const themeScript = `try{if(localStorage.getItem("theme")==="dark")document.documentElement.dataset.theme="dark"}catch(e){}`;

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className={`${sans.variable} ${serif.variable} antialiased`}>{children}</body>
    </html>
  );
}
