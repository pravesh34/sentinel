import "./globals.css";
import React from "react";

export const metadata = { title: "SENTINEL — Agentic Workflow Engine", description: "Autonomy with accountability" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0f1115] text-zinc-100 antialiased">{children}</body>
    </html>
  );
}
