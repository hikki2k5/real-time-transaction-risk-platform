import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Risk Platform Dashboard",
  description: "Local fraud detection platform dashboard"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
