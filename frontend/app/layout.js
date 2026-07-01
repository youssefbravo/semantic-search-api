import "./globals.css";

export const metadata = {
  title: "Document Semantic Search",
  description:
    "Search documents by meaning — compare BM25, semantic, and hybrid retrieval side by side.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-indigo-500/30">
        {children}
      </body>
    </html>
  );
}
