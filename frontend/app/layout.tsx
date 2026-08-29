import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NTU Exchange Planner",
  description: "Plan GEM Explorer and SUSEP with previously mapped modules.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
