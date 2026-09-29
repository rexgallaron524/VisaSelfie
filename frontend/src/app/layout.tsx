import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Visa Selfie", template: "%s · Visa Selfie" },
  description: "A private workspace for visa applicant video verification.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
