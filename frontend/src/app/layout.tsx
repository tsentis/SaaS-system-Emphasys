import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Emphasys — European Project Intelligence",
  description: "AI-powered analysis of European project proposals.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
