import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { QueryProvider } from '@/components/providers/QueryProvider';
import { ThemeProvider } from '@/components/providers/ThemeProvider';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'AI Documentation Gap Finder',
  description: 'Automatically detect and fix documentation gaps in your codebase',
  keywords: ['documentation', 'AI', 'gap analysis', 'developer tools'],
  authors: [{ name: 'AI DocGap Team' }],
  viewport: 'width=device-width, initial-scale=1',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} antialiased`}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryProvider>
            <div className="min-h-screen bg-background">
              <main>{children}</main>
            </div>
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
