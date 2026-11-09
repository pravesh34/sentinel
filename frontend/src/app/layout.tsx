import "./globals.css";
import React from "react";
import Nav from "@/components/Nav";

export const metadata = { title: "SENTINEL — Agentic Workflow Engine", description: "Autonomy with accountability. Give it a goal — it plans, runs tools safely, watches your budget, and asks before anything risky." };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-[#0f1115] text-zinc-100 antialiased">
        <Nav />
        {children}
      </body>
    </html>
  );
}
