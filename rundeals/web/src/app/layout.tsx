import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RunDeals — Running Shoe Deals",
  description: "Aggregated running shoe deals from top brands and retailers",
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
