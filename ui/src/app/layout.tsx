import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Codebase Tutorial Generator",
  description: "AI-powered tutorials for any codebase",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="overflow-x-hidden">
      <body className={`${inter.className} min-h-screen max-w-[100vw] overflow-x-hidden bg-slate-950 text-white antialiased`}>
        <Header />
        <main className="pt-16 max-w-[100vw] overflow-x-hidden">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
