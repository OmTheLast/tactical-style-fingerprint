import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Tactical Style Fingerprint",
  description: "Transparent event-data tactical fingerprints for Premier League 2015/16 teams.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
