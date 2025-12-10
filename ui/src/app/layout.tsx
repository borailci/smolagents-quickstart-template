import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";
import { ThemeProvider } from "@/hooks/useTheme";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata: Metadata = {
  title: "Codebase Tutorial Generator | AI-Powered Learning Paths",
  description: "Transform complex codebases into comprehensive, easy-to-follow tutorials using AI agents. Learn faster with structured, visual learning paths.",
  keywords: ["AI", "tutorial", "codebase", "learning", "documentation", "agents"],
  authors: [
    { name: "Amir Kiarafi", url: "https://github.com/amirkiarafiei" },
    { name: "Bora Ilci", url: "https://github.com/borailci" },
  ],
  openGraph: {
    title: "Codebase Tutorial Generator",
    description: "AI-powered codebase to tutorial transformation",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} font-sans antialiased min-h-screen flex flex-col`}>
        <ThemeProvider>
          <Header />
          <main className="flex-1 pt-16">
            {children}
          </main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}
