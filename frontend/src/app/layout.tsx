import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NASA AI Mission Control",
  description: "Multi-agent NASA briefing console over MCP tools",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
