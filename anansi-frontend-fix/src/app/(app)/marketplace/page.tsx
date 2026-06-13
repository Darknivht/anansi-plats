"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import { useMarketplaceStore } from "../../../stores/marketplace";
import type { SortOption, MarketplaceListing } from "../../../stores/marketplace";
import { ListingCard } from "../../../components/marketplace/ListingCard";
import { InstallModal } from "../../../components/marketplace/InstallModal";
import { GlassCard } from "../../../components/ui/GlassCard";
import { AnansiButton } from "../../../components/ui/AnansiButton";
import { Skeleton } from "../../../components/ui/Skeleton";
import {
  Search,
  SlidersHorizontal,
  X,
  Filter,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  TrendingUp,
  Clock,
  Star,
  DollarSign,
} from "lucide-react";
import { cn } from "../../../lib/utils";

// ─── Sort Options ────────────────────────────────────────────────────────────

const SORT_OPTIONS: { value: SortOption; label: string; icon: React.ReactNode }[] = [
  { value: "popular", label: "Popular", icon: <TrendingUp className="h-4 w-4" /> },
  { value: "newest", label: "Newest", icon: <Clock className="h-4 w-4" /> },
  { value: "rating", label: "Top Rated", icon: <Star className="h-4 w-4" /> },
  { value: "price_low", label: "Price: Low", icon: <DollarSign className="h-4 w-4" /> },
  { value: "price_high", label: "Price: High", icon: <DollarSign className="h-4 w-4" /> },
];

// ─── Price Filter Options ────────────────────────────────────────────────────

const PRICE_FILTERS = [
  { value: null, label: "All" },
  { value: "free" as const, label: "Free" },
  { value: "paid" as const, label: "Paid" },
];

// ─── Skeleton Loading Card ───────────────────────────────────────────────────

function ListingCardSkeleton() {
  return (
    <GlassCard variant="base" padding="md" className="space-y-3">
      <Skeleton className="w-full h-32 rounded-lg" />
      <Skeleton className="w-3/4 h-4 rounded" />
      <Skeleton className="w-1/2 h-3 rounded" />
      <div className="flex justify-between">
        <Skeleton className="w-20 h-4 rounded" />
        <Skeleton className="w-16 h-4 rounded" />
      </div>
      <Skeleton className="w-24 h-8 rounded-lg" />
    </GlassCard>
  );
}

// ─── Marketplace Browse Page ─────────────────────────────────────────────────

export default function MarketplacePage() {
  const router = useRouter();
  const {
    listings,
    totalListings,
    currentPage,
    totalPages,
    categories,
    featuredListings,
    filters,
    isLoading,
    isInstalling,
    fetchListings,
    fetchCategories,
    fetchFeatured,
    setFilters,
    clearFilters,
    installAgent,
  } = useMarketplaceStore();

  const [searchQuery, setSearchQuery] = useState(filters.search || "");
  const [showFilters, setShowFilters] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(filters.category);
  const [priceFilter, setPriceFilter] = useState<"free" | "paid" | null>(null);
  const [installModalOpen, setInstallModalOpen] = useState(false);
  const [installListing, setInstallListing] = useState<MarketplaceListing | null>(null);

  // Load initial data
  useEffect(() => {
    fetchListings(1);
    fetchCategories();
    fetchFeatured();
  }, [fetchListings, fetchCategories, fetchFeatured]);

  // ── Handlers ──

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setFilters({ search: searchQuery });
    },
    [searchQuery, setFilters]
  );

  const handleSort = useCallback(
    (sort: SortOption) => {
      setFilters({ sort });
    },
    [setFilters]
  );

  const handleCategoryClick = useCallback(
    (slug: string | null) => {
      const newCategory = slug === selectedCategory ? null : slug;
      setSelectedCategory(newCategory);
      setFilters({ category: newCategory });
    },
    [selectedCategory, setFilters]
  );

  const handlePriceFilter = useCallback(
    (value: "free" | "paid" | null) => {
      setPriceFilter(value);
      if (value === "free") {
        setFilters({ price_min: 0, price_max: 0 });
      } else if (value === "paid") {
        setFilters({ price_min: 1, price_max: null });
      } else {
        setFilters({ price_min: null, price_max: null });
      }
    },
    [setFilters]
  );

  const handleInstall = useCallback(
    async (listing: MarketplaceListing) => {
      setInstallListing(listing);
      setInstallModalOpen(true);
    },
    []
  );

  const handleConfirmInstall = useCallback(async () => {
    if (!installListing) return;
    const result = await installAgent(installListing.id);
    if (result) {
      // After install, let the modal show success
      return;
    }
    throw new Error("Installation failed");
  }, [installListing, installAgent]);

  const handlePageChange = useCallback(
    (page: number) => {
      if (page >= 1 && page <= totalPages) {
        fetchListings(page);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    },
    [totalPages, fetchListings]
  );

  const handleClearFilters = useCallback(() => {
    setSearchQuery("");
    setSelectedCategory(null);
    setPriceFilter(null);
    clearFilters();
  }, [clearFilters]);

  // Check if any filters are active
  const hasActiveFilters = filters.category || filters.sort !== "popular" || priceFilter || filters.search;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            Marketplace
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Discover and install AI agents for every aspect of your life
          </p>
        </div>
        <Sparkles className="h-8 w-8 text-[var(--color-brand-amber)]" />
      </div>

      {/* Featured Section */}
      {featuredListings.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)] mb-3 flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-[var(--color-brand-amber)]" />
            Featured Agents
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {featuredListings.slice(0, 5).map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                onInstall={() => handleInstall(listing)}
              />
            ))}
          </div>
        </section>
      )}

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="relative">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--color-text-muted)]" />
        <input
          type="text"
          placeholder="Search marketplace agents..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className={cn(
            "w-full pl-12 pr-12 py-3.5 rounded-xl text-sm",
            "bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)]",
            "text-[var(--color-text-primary)] placeholder:text-[var(--color-text-disabled)]",
            "focus:outline-none focus:border-amber-500/40 focus:ring-2 focus:ring-amber-500/10",
            "transition-all"
          )}
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1">
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              "p-2 rounded-lg transition-colors",
              showFilters
                ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)]"
                : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5"
            )}
            aria-label="Toggle filters"
          >
            <SlidersHorizontal className="h-4 w-4" />
          </button>
        </div>
      </form>

      {/* Filter Bar (collapsible) */}
      {showFilters && (
        <GlassCard variant="base" padding="md" className="space-y-4 animate-in slide-in-from-top-2 duration-200">
          {/* Categories */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2 flex items-center gap-1.5">
              <Filter className="h-3.5 w-3.5" />
              Categories
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => handleCategoryClick(null)}
                className={cn(
                  "text-xs px-3 py-1.5 rounded-full transition-colors",
                  selectedCategory === null
                    ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)] border border-amber-500/30"
                    : "bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-amber-500/20"
                )}
              >
                All
              </button>
              {categories.map((cat) => (
                <button
                  key={cat.slug}
                  onClick={() => handleCategoryClick(cat.slug)}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-full transition-colors",
                    selectedCategory === cat.slug
                      ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)] border border-amber-500/30"
                      : "bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-amber-500/20"
                  )}
                >
                  {cat.display_name} ({cat.count})
                </button>
              ))}
            </div>
          </div>

          {/* Price */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
              Price
            </p>
            <div className="flex gap-2">
              {PRICE_FILTERS.map((pf) => (
                <button
                  key={pf.label}
                  onClick={() => handlePriceFilter(pf.value)}
                  className={cn(
                    "text-xs px-3 py-1.5 rounded-full transition-colors",
                    priceFilter === pf.value
                      ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)] border border-amber-500/30"
                      : "bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-amber-500/20"
                  )}
                >
                  {pf.label}
                </button>
              ))}
            </div>
          </div>

          {/* Active filters clear */}
          {hasActiveFilters && (
            <div className="pt-1">
              <button
                onClick={handleClearFilters}
                className="text-xs text-[var(--color-text-muted)] hover:text-red-400 transition-colors flex items-center gap-1"
              >
                <X className="h-3 w-3" />
                Clear all filters
              </button>
            </div>
          )}
        </GlassCard>
      )}

      {/* Sort + Results info */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-[var(--color-text-muted)]">
          {totalListings > 0 ? `${totalListings} agent${totalListings !== 1 ? "s" : ""} found` : ""}
        </p>
        <div className="flex items-center gap-1">
          {SORT_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => handleSort(opt.value)}
              className={cn(
                "flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg transition-colors",
                filters.sort === opt.value
                  ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5"
              )}
            >
              {opt.icon}
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Grid of Agent Cards */}
      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <ListingCardSkeleton key={i} />
          ))}
        </div>
      ) : listings.length === 0 ? (
        <div className="text-center py-16 space-y-3">
          <Search className="h-12 w-12 mx-auto text-[var(--color-text-disabled)]" />
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
            No agents found
          </h3>
          <p className="text-sm text-[var(--color-text-muted)] max-w-md mx-auto">
            {filters.search
              ? `No results for "${filters.search}". Try a different search term or clear filters.`
              : "No agents match your filters. Try different categories or sort options."}
          </p>
          {hasActiveFilters && (
            <AnansiButton variant="secondary" size="sm" onClick={handleClearFilters}>
              Clear Filters
            </AnansiButton>
          )}
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {listings.map((listing) => (
            <ListingCard
              key={listing.id}
              listing={listing}
              onInstall={() => handleInstall(listing)}
              isInstalling={isInstalling}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage <= 1}
            icon={<ChevronLeft className="h-4 w-4" />}
          >
            Previous
          </AnansiButton>

          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            // Show pages around current
            let pageNum: number;
            if (totalPages <= 7) {
              pageNum = i + 1;
            } else if (currentPage <= 4) {
              pageNum = i + 1;
            } else if (currentPage >= totalPages - 3) {
              pageNum = totalPages - 6 + i;
            } else {
              pageNum = currentPage - 3 + i;
            }
            return (
              <button
                key={pageNum}
                onClick={() => handlePageChange(pageNum)}
                className={cn(
                  "w-8 h-8 rounded-lg text-xs font-medium transition-colors",
                  pageNum === currentPage
                    ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)]"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5"
                )}
              >
                {pageNum}
              </button>
            );
          })}

          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage >= totalPages}
            icon={<ChevronRight className="h-4 w-4" />}
          >
            Next
          </AnansiButton>
        </div>
      )}

      {/* Install Modal */}
      <InstallModal
        listing={installListing}
        isOpen={installModalOpen}
        isInstalling={isInstalling}
        onClose={() => {
          setInstallModalOpen(false);
          setInstallListing(null);
        }}
        onConfirm={handleConfirmInstall}
      />
    </div>
  );
}
