import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Codebase Tutorial Generator",
  description: "Browse AI-generated codebase tutorials",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} min-h-screen flex flex-col bg-[url('/grid.svg')] bg-fixed`}>
        {/* Grid background pattern placeholder, if grid.svg missing it will just use bg-background from globals */}
        <div className="fixed inset-0 z-[-1] bg-background opacity-90" />
        <Header />
        <main className="flex-1 w-full pt-20 pb-10 custom-scrollbar">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
