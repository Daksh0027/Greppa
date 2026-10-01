import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Greppa | Large-Repo Code Intelligence Engine",
  description: "Never feed the whole codebase to a model. Build an index once, retrieve only what each question needs.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-zinc-950 text-zinc-100 min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
