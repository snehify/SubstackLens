import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Substack Search",
  description: "Independent keyword search across indexed public Substack posts."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
