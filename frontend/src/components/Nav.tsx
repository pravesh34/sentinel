"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";

export default function Nav() {
  const path = usePathname();
  const link = (href: string, label: string) => (
    <Link
      key={href}
      href={href}
      className={`px-3 py-1.5 rounded-lg text-sm ${path === href ? "bg-[#7c6cff] text-white" : "text-zinc-300 hover:bg-zinc-800"}`}
    >
      {label}
    </Link>
  );
  return (
    <header className="sticky top-0 z-10 bg-[#0f1115]/90 backdrop-blur border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="font-bold text-lg">SENTINEL</Link>
          <span className="hidden md:inline text-xs text-zinc-500">Agentic Workflow Engine</span>
        </div>
        <nav className="flex items-center gap-1">
          {link("/", "Dashboard")}
          {link("/tutorial", "Tutorial")}
          <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="px-3 py-1.5 rounded-lg text-sm text-zinc-300 hover:bg-zinc-800">API Docs</a>
        </nav>
      </div>
    </header>
  );
}
