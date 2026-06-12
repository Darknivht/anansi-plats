"use client";

import { type ReactNode, useCallback } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { GlassCard } from "@/components/ui/GlassCard";
import {
  Star,
  Download,
  ExternalLink,
  ShoppingCart,
  Loader2,
} from "lucide-react";
import type { MarketplaceListing } from "@/stores/marketplace";

// ─── Rating Stars ────────────────────────────────────────────────────────────

function RatingStars({ rating, count, size = "sm" }: { rating: number; count: number; size?: "sm" | "md" }) {
  const starSize = size === "md" ? "h-5 w-5" : "h-3.5 w-3.5";
  const textSize = size === "md" ? "text-sm" : "text-xs";

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = rating >= star;
        const half = !filled && rating >= star - 0.5;
        return (
          <Star
            key={star}
            className={cn(
              starSize,
              filled
                ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]"
                : half
                  ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]/30"
                  : "text-[var(--color-text-disabled)]"
            )}
          />
        );
      })}
      {count > 0 && (
        <span className={cn(textSize, "text-[var(--color-text-muted)] ml-1")}>
          ({count})
        </span>
      )}
    </div>
  );
}

// ─── Price Badge ─────────────────────────────────────────────────────────────

function PriceBadge({ price_cents }: { price_cents: number }) {
  if (price_cents === 0) {
    return (
      <span className="text-xs font-medium text-emerald-400 bg-emerald-400/10 px-2 py-0.5 rounded-full">
        Free
      </span>
    );
  }
  return (
    <span className="text-sm font-bold text-[var(--color-text-primary)]">
      ${(price_cents / 100).toFixed(2)}
    </span>
  );
}

// ─── Listing Card ────────────────────────────────────────────────────────────

interface ListingCardProps {
  listing: MarketplaceListing;
  onInstall?: (listingId: string) => void;
  isInstalling?: boolean;
}

export function ListingCard({ listing, onInstall, isInstalling }: ListingCardProps) {
  const handleInstall = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      e.stopPropagation();
      onInstall?.(listing.id);
    },
    [listing.id, onInstall]
  );

  return (
    <Link href={`/marketplace/${listing.id}`} className="block group">
      <GlassCard
        variant="interactive"
        padding="md"
        className={cn(
          "relative overflow-hidden transition-all duration-300",
          "group-hover:translate-y-[-4px] group-hover:shadow-[0_0_30px_rgba(245,158,11,0.15)]",
          "group-hover:border-amber-500/30"
        )}
      >
        {/* Thumbnail / Color gradient placeholder */}
        <div className="w-full h-32 rounded-lg mb-3 bg-gradient-to-br from-[var(--color-brand-amber)]/20 to-[var(--color-spirit-violet)]/20 flex items-center justify-center overflow-hidden">
          {listing.screenshots && listing.screenshots[0] ? (
            <img
              src={listing.screenshots[0]}
              alt={listing.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="text-3xl opacity-30">
              {listing.category?.[0]?.toUpperCase() || "A"}
            </div>
          )}
        </div>

        {/* Featured badge */}
        {listing.is_featured && (
          <div className="absolute top-2 right-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-[var(--color-brand-amber)] bg-[var(--color-bg-surface)]/80 backdrop-blur-sm px-2 py-0.5 rounded-full border border-amber-500/30">
              Featured
            </span>
          </div>
        )}

        {/* Title & Creator */}
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate mb-0.5 group-hover:text-[var(--color-brand-amber)] transition-colors">
          {listing.title}
        </h3>
        <p className="text-xs text-[var(--color-text-muted)] mb-2 truncate">
          by {listing.agent_name || "Unknown"}
        </p>

        {/* Rating & Install count */}
        <div className="flex items-center justify-between mb-3">
          <RatingStars rating={listing.rating_avg} count={listing.rating_count} />
          <div className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
            <Download className="h-3 w-3" />
            <span>{listing.install_count}</span>
          </div>
        </div>

        {/* Price + Install button */}
        <div className="flex items-center justify-between">
          <PriceBadge price_cents={listing.price_cents} />
          <AnansiButton
            variant="secondary"
            size="sm"
            icon={isInstalling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShoppingCart className="h-3.5 w-3.5" />}
            onClick={handleInstall}
            disabled={isInstalling}
            className="opacity-0 group-hover:opacity-100 transition-opacity duration-200"
          >
            {isInstalling ? "Installing..." : "Install"}
          </AnansiButton>
        </div>

        {/* Agent info on hover */}
        <div className="absolute inset-0 rounded-[inherit] pointer-events-none ring-1 ring-inset ring-transparent group-hover:ring-amber-500/20 transition-all duration-300" />
      </GlassCard>
    </Link>
  );
}

// ─── Exports ─────────────────────────────────────────────────────────────────

export { RatingStars, PriceBadge };
