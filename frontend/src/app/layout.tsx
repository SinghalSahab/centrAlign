import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "CentrAlign | Autonomous AI Employee Platform",
  description: "Generic AI Agent runtime with ground-truth verification, role playbooks, and sandbox company web apps.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark bg-slate-950 text-slate-100 antialiased">
      <body className={`${inter.className} min-h-screen flex flex-col bg-slate-950 selection:bg-blue-600 selection:text-white`}>
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto p-4 md:p-6 lg:p-8">
          {children}
        </main>
        <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-400">
          CentrAlign Autonomous AI Employee Platform Prototype &bull; Understand &bull; Connect &bull; Configure &bull; Deploy
        </footer>
      </body>
    </html>
  );
}
