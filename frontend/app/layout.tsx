import type { Metadata, Viewport } from "next";
import Script from "next/script";
import "./globals.css";

export const metadata: Metadata = {
  title: "Insurance Verify",
  description: "Scan a dental insurance card and get a verified benefit summary.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#020617" },
  ],
};

// Restores the saved theme before paint so the page never flashes the wrong one.
const themeScript = `
(function () {
  try {
    var t = localStorage.getItem("insurance-verify-theme");
    var dark = t === "dark" || ((!t || t === "system") &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
    var d = document.documentElement;
    d.classList.toggle("dark", dark);
    d.style.colorScheme = dark ? "dark" : "light";
  } catch (e) {}
})();
`;

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head />
      <body>
        <Script
          id="theme-init"
          strategy="beforeInteractive"
          dangerouslySetInnerHTML={{ __html: themeScript }}
        />
        {children}
      </body>
    </html>
  );
}
