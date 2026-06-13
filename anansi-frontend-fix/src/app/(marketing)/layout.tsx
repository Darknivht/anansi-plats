import { BrainIcon } from "../../components/ui/BrainIcon";
import Link from "next/link";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Navigation */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[var(--color-bg-deepest)]/80 backdrop-blur-xl border-b border-[var(--color-border-subtle)]">
        <nav className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <BrainIcon size={24} active glow="amber" />
            <span className="text-lg font-heading font-bold text-[var(--color-text-primary)]">
              anansi
            </span>
          </Link>

          <div className="flex items-center gap-4 sm:gap-8">
            <a
              href="#features"
              className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors hidden sm:block"
            >
              Features
            </a>
            <a
              href="#pricing"
              className="text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors hidden sm:block"
            >
              Pricing
            </a>
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="text-sm font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="inline-flex items-center px-4 py-2 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-brand-amber to-brand-amber-light hover:shadow-glow-amber transition-all duration-200 ease-anansi"
              >
                Get Started
              </Link>
            </div>
          </div>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 pt-16">{children}</main>
    </div>
  );
}
