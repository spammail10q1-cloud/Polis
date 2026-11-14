import type { Metadata, Viewport } from "next";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource-variable/newsreader";
import "@fontsource-variable/newsreader/wght-italic.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";
import { ToastProvider } from "@/components/toast";

export const metadata: Metadata = {
  title: {
    default: "POLIS · Your body, your biology, your digital twin",
    template: "%s · POLIS",
  },
  description:
    "A privacy-preserving, evidence-grounded digital twin of your biology. Experimental research platform; demonstration data are synthetic.",
  applicationName: "POLIS",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: "#0b0e0c",
  colorScheme: "dark",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ToastProvider>
          <AuthProvider>{children}</AuthProvider>
        </ToastProvider>
      </body>
    </html>
  );
}
