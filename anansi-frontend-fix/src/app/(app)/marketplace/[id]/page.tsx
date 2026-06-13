"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMarketplaceStore } from "../../../../stores/marketplace";
import type { MarketplaceListingDetail } from "../../../../stores/marketplace";
import { ReviewSection } from "../../../../components/marketplace/ReviewSection";
import { InstallModal } from "../../../../components/marketplace/InstallModal";
import { GlassCard } from "../../../../components/ui/GlassCard";
import { AnansiButton } from "../../../../components/ui/AnansiButton";
import { Skeleton } from "../../../../components/ui/Skeleton";
import {
  ArrowLeft,
  Download,
  Star,
  ShoppingCart,
  Clock,
  Tag,
  Grid3X3,
  User,
  ExternalLink,
  AlertCircle,
  Loader2,
  Sparkles,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { cn } from "../../../../lib/utils";

// ─── Skeleton Loader ─────────────────────────────────────────────────────────

function DetailSkeleton() {
  return (
    <div className="space-y-6 animate-pulse">
      <Skeleton className="w-24 h-6 rounded" />
      <Skeleton className="w-full h-64 rounded-xl" />
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <Skeleton className="w-3/4 h-8 rounded" />
          <Skeleton className="w-1/2 h-4 rounded" />
          <Skeleton className="w-full h-40 rounded-lg" />
        </div>
        <div className="space-y-4">
          <Skeleton className="w-full h-48 rounded-xl" />
        </div>
      </div>
    </div>
  );
}

// ─── Screenshot Carousel ─────────────────────────────────────────────────────

function ScreenshotCarousel({ screenshots }: { screenshots: string[] }) {
  const [current, setCurrent] = useState(0);

  if (!screenshots || screenshots.length === 0) {
    return (
      <div className="w-full h-64 rounded-xl bg-gradient-to-br from-[var(--color-brand-amber)]/10 to-[var(--color-spirit-violet)]/10 flex items-center justify-center">
        <div className="text-center text-[var(--color-text-muted)]">
          <Grid3X3 className="h-12 w-12 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No screenshots available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-64 rounded-xl overflow-hidden group">
      <img
        src={screenshots[current]}
        alt={`Screenshot ${current + 1}`}
        className="w-full h-full object-cover transition-opacity duration-300"
      />

      {screenshots.length > 1 && (
        <>
          <button
            onClick={() => setCurrent((c) => Math.max(0, c - 1))}
            disabled={current === 0}
            className="absolute left-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-0"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            onClick={() => setCurrent((c) => Math.min(screenshots.length - 1, c + 1))}
            disabled={current === screenshots.length - 1}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg bg-black/40 text-white opacity-0 group-hover:opacity-100 transition-opacity disabled:opacity-0"
          >
            <ChevronRight className="h-5 w-5" />
          </button>

          <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
            {screenshots.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={cn(
                  "w-2 h-2 rounded-full transition-all",
                  i === current
                    ? "bg-white w-4"
                    : "bg-white/40 hover:bg-white/60"
                )}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Listing Detail Page ─────────────────────────────────────────────────────

export default function ListingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const listingId = params.id as string;

  const {
    selectedListing,
    isLoading,
    isInstalling,
    isSubmittingReview,
    fetchListingDetail,
    installAgent,
    submitReview,
  } = useMarketplaceStore();

  const [installModalOpen, setInstallModalOpen] = useState(false);

  useEffect(() => {
    if (listingId) {
      fetchListingDetail(listingId);
    }
  }, [listingId, fetchListingDetail]);

  const handleInstall = useCallback(async () => {
    if (!selectedListing) return;
    const result = await installAgent(selectedListing.id);
    if (result) return;
    throw new Error("Installation failed");
  }, [selectedListing, installAgent]);

  const handleSubmitReview = useCallback(
    async (rating: number, review?: string) => {
      if (!selectedListing) return;
      await submitReview(selectedListing.id, rating, review);
    },
    [selectedListing, submitReview]
  );

  // ── Loading ──
  if (isLoading && !selectedListing) {
    return <DetailSkeleton />;
  }

  // ── Error ──
  if (!isLoading && !selectedListing) {
    return (
      <div className="text-center py-16 space-y-3">
        <AlertCircle className="h-12 w-12 mx-auto text-red-400" />
        <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
          Listing Not Found
        </h3>
        <p className="text-sm text-[var(--color-text-muted)]">
          This marketplace listing doesn&apos;t exist or has been removed.
        </p>
        <AnansiButton
          variant="secondary"
          size="sm"
          onClick={() => router.push("/marketplace")}
        >
          Back to Marketplace
        </AnansiButton>
      </div>
    );
  }

  const listing = selectedListing as MarketplaceListingDetail;

  return (
    <div className="space-y-6">
      {/* Back Button */}
      <button
        onClick={() => router.push("/marketplace")}
        className="flex items-center gap-2 text-sm text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Marketplace
      </button>

      {/* Hero Section: Screenshots + Basic Info */}
      <div className="space-y-4">
        <ScreenshotCarousel screenshots={listing.screenshots} />

        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          {/* Title, Creator, Rating */}
          <div className="space-y-2">
            <h1 className="text-2xl lg:text-3xl font-heading font-bold text-[var(--color-text-primary)]">
              {listing.title}
            </h1>
            <div className="flex items-center gap-4 text-sm text-[var(--color-text-muted)]">
              <div className="flex items-center gap-1.5">
                <User className="h-4 w-4" />
                <span>{listing.creator?.display_name || "Unknown"}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Star className="h-4 w-4 text-[var(--color-brand-amber)]" />
                <span className="font-medium text-[var(--color-text-primary)]">
                  {listing.rating_avg.toFixed(1)}
                </span>
                <span>({listing.rating_count})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Download className="h-4 w-4" />
                <span>{listing.install_count} installs</span>
              </div>
            </div>
            {listing.is_featured && (
              <div className="flex items-center gap-1 text-xs text-[var(--color-brand-amber)]">
                <Sparkles className="h-3.5 w-3.5" />
                Featured Agent
              </div>
            )}
          </div>

          {/* Install Button */}
          <div className="flex items-center gap-3 lg:flex-col">
            <AnansiButton
              variant="primary"
              size="lg"
              icon={isInstalling ? <Loader2 className="h-5 w-5 animate-spin" /> : <ShoppingCart className="h-5 w-5" />}
              onClick={() => setInstallModalOpen(true)}
              disabled={isInstalling}
              className="w-full lg:w-auto min-w-[160px]"
            >
              {isInstalling
                ? "Installing..."
                : `Install ${listing.price_cents > 0 ? `- $${(listing.price_cents / 100).toFixed(2)}` : "(Free)"}`}
            </AnansiButton>
            {listing.agent_version && (
              <span className="text-xs text-[var(--color-text-muted)]">
                Version {listing.agent_version}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Description + Version History + Reviews */}
        <div className="lg:col-span-2 space-y-6">
          {/* Description */}
          <GlassCard variant="base" padding="lg" className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
              About This Agent
            </h2>
            {listing.description ? (
              <div className="prose prose-sm prose-invert max-w-none text-[var(--color-text-secondary)] leading-relaxed whitespace-pre-wrap">
                {listing.description}
              </div>
            ) : (
              <p className="text-sm text-[var(--color-text-muted)] italic">
                No description provided.
              </p>
            )}

            {/* Memory impact estimate */}
            {(listing.memory_nodes_per_run || listing.memory_links_per_run) && (
              <div className="bg-[var(--color-bg-deepest)]/40 rounded-lg p-3 text-xs text-[var(--color-text-muted)] space-y-1">
                <p className="font-medium text-[var(--color-text-secondary)]">
                  Memory Impact
                </p>
                {listing.memory_nodes_per_run && (
                  <p>~{listing.memory_nodes_per_run} memory nodes created per run</p>
                )}
                {listing.memory_links_per_run && (
                  <p>~{listing.memory_links_per_run} connections formed per run</p>
                )}
              </div>
            )}
          </GlassCard>

          {/* Version History */}
          {listing.version_history && listing.version_history.length > 0 && (
            <GlassCard variant="base" padding="lg" className="space-y-3">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                <Clock className="h-5 w-5 text-[var(--color-text-muted)]" />
                Version History
              </h2>
              <div className="space-y-2">
                {listing.version_history.map((vh) => (
                  <div
                    key={vh.version}
                    className="flex items-center justify-between py-2 border-b border-[var(--color-border-subtle)] last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-medium text-[var(--color-text-primary)]">
                        v{vh.version}
                      </span>
                      {vh.change_notes && (
                        <span className="text-xs text-[var(--color-text-secondary)]">
                          {vh.change_notes}
                        </span>
                      )}
                    </div>
                    <span className="text-xs text-[var(--color-text-muted)]">
                      {vh.created_at
                        ? new Date(vh.created_at).toLocaleDateString()
                        : ""}
                    </span>
                  </div>
                ))}
              </div>
            </GlassCard>
          )}

          {/* Reviews */}
          <ReviewSection
            reviews={listing.reviews}
            listingId={listing.id}
            onSubmitReview={handleSubmitReview}
            isSubmitting={isSubmittingReview}
            isAuthenticated={true}
          />
        </div>

        {/* Right Sidebar: Category, Tags, Metadata */}
        <div className="space-y-4">
          <GlassCard variant="base" padding="md" className="space-y-4">
            {/* Category */}
            {listing.category && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5 flex items-center gap-1">
                  <Grid3X3 className="h-3.5 w-3.5" />
                  Category
                </p>
                <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                  {listing.category.replace("_", " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                </span>
              </div>
            )}

            {/* Tags */}
            {listing.tags && listing.tags.length > 0 && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5 flex items-center gap-1">
                  <Tag className="h-3.5 w-3.5" />
                  Tags
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {listing.tags.map((tag) => (
                    <span
                      key={tag}
                      className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2 py-0.5 rounded-full"
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Price */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5">
                Price
              </p>
              <span className={cn(
                "text-lg font-bold",
                listing.price_cents === 0
                  ? "text-emerald-400"
                  : "text-[var(--color-text-primary)]"
              )}>
                {listing.price_display}
              </span>
            </div>

            {/* Last Updated */}
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5">
                Last Updated
              </p>
              <p className="text-sm text-[var(--color-text-secondary)]">
                {listing.updated_at
                  ? new Date(listing.updated_at).toLocaleDateString("en-US", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })
                  : "N/A"}
              </p>
            </div>

            {/* Agent ID */}
            {listing.agent_id && (
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-1.5">
                  Agent Version
                </p>
                <p className="text-sm text-[var(--color-text-secondary)] font-mono">
                  v{listing.agent_version || "1.0"}
                </p>
              </div>
            )}
          </GlassCard>
        </div>
      </div>

      {/* Install Modal */}
      <InstallModal
        listing={listing}
        isOpen={installModalOpen}
        isInstalling={isInstalling}
        onClose={() => setInstallModalOpen(false)}
        onConfirm={handleInstall}
      />
    </div>
  );
}
