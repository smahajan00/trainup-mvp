import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "TrainUp",
  description: "AI-Powered Multi-Sport Coaching Platform"
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body>{children}</body>
    </html>
  );
}
