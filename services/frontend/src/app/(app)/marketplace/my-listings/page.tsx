"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useMarketplaceStore } from "@/stores/marketplace";
import type { SalesAnalytics, CreatorListing, EarningsData, MarketplaceReview } from "@/stores/marketplace";
import { GlassCard } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  Package,
  Download,
  DollarSign,
  Star,
  TrendingUp,
  TrendingDown,
  Wallet,
  Clock,
  BarChart3,
  ExternalLink,
  ChevronRight,
  MessageSquare,
  Eye,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Stat Card ───────────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sublabel,
  trend,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sublabel?: string;
  trend?: "up" | "down" | null;
}) {
  return (
    <GlassCard variant="base" padding="md" className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-[var(--color-text-muted)]">
          {label}
        </span>
        <span className={cn(
          "p-1.5 rounded-lg",
          trend === "up" ? "bg-emerald-400/10 text-emerald-400"
            : trend === "down" ? "bg-red-400/10 text-red-400"
            : "bg-[var(--color-bg-deepest)] text-[var(--color-text-muted)]"
        )}>
          {icon}
        </span>
      </div>
      <p className="text-2xl font-bold text-[var(--color-text-primary)]">
        {value}
      </p>
      {sublabel && (
        <p className="text-xs text-[var(--color-text-muted)]">{sublabel}</p>
      )}
      {trend === "up" && (
        <div className="flex items-center gap-1 text-xs text-emerald-400">
          <TrendingUp className="h-3 w-3" />
          <span>Up this period</span>
        </div>
      )}
      {trend === "down" && (
        <div className="flex items-center gap-1 text-xs text-red-400">
          <TrendingDown className="h-3 w-3" />
          <span>Down this period</span>
        </div>
      )}
    </GlassCard>
  );
}

// ─── Simple Bar Chart ────────────────────────────────────────────────────────

function SimpleBarChart({
  data,
  accent = "amber",
}: {
  data: { date: string; installs: number }[];
  accent?: "amber" | "violet" | "teal";
}) {
  if (!data || data.length === 0) {
    return (
      <div className="h-32 flex items-center justify-center text-sm text-[var(--color-text-muted)]">
        No data available yet
      </div>
    );
  }

  const maxVal = Math.max(...data.map((d) => d.installs), 1);
  const accentColors = {
    amber: "from-[var(--color-brand-amber)] to-[var(--color-brand-amber-light)]",
    violet: "from-[var(--color-spirit-violet)] to-[var(--color-spirit-violet)]/70",
    teal: "from-[var(--color-deep-teal)] to-[var(--color-deep-teal)]/70",
  };

  return (
    <div className="h-32 flex items-end gap-1">
      {data.map((d, i) => (
        <div
          key={d.date}
          className="flex-1 flex flex-col items-center gap-1 group relative"
        >
          <div
            className={cn(
              "w-full rounded-t-sm transition-all duration-200",
              "bg-gradient-to-t",
              accentColors[accent],
            )}
            style={{
              height: `${Math.max((d.installs / maxVal) * 100, 2)}%`,
              opacity: 0.6 + (d.installs / maxVal) * 0.4,
            }}
          />
          {/* Tooltip on hover */}
          <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-[var(--color-bg-surface)] border border-[var(--color-border-subtle)] rounded px-2 py-1 text-xs opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
            {d.installs} installs
            <br />
            {new Date(d.date).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Listing Row ─────────────────────────────────────────────────────────────

function ListingRow({
  listing,
}: {
  listing: CreatorListing;
}) {
  return (
    <Link
      href={`/marketplace/${listing.id}`}
      className="flex items-center justify-between py-3 px-4 rounded-lg hover:bg-white/5 transition-colors group"
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
            {listing.title}
          </p>
          <span className={cn(
            "text-[10px] px-1.5 py-0.5 rounded-full font-medium",
            listing.is_published
              ? "bg-emerald-400/10 text-emerald-400"
              : listing.status === "rejected"
                ? "bg-red-400/10 text-red-400"
                : "bg-amber-400/10 text-amber-400"
          )}>
            {listing.is_published ? "Published" : listing.status}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-[var(--color-text-muted)]">
          <span>{listing.category || "Uncategorized"}</span>
          <span className="flex items-center gap-1">
            <Download className="h-3 w-3" /> {listing.install_count}
          </span>
          <span className="flex items-center gap-1">
            <Star className="h-3 w-3" /> {listing.rating_avg.toFixed(1)}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold text-[var(--color-text-primary)]">
          {listing.price_display}
        </span>
        <ChevronRight className="h-4 w-4 text-[var(--color-text-disabled)] group-hover:text-[var(--color-text-muted)] transition-colors" />
      </div>
    </Link>
  );
}

// ─── Creator Dashboard Page ──────────────────────────────────────────────────

export default function MyListingsPage() {
  const {
    myListings,
    analytics,
    earnings,
    creatorReviews,
    isLoading,
    fetchMyListings,
    fetchAnalytics,
    fetchEarnings,
    fetchCreatorReviews,
  } = useMarketplaceStore();

  const [analyticsPeriod, setAnalyticsPeriod] = useState("30d");

  useEffect(() => {
    fetchMyListings();
    fetchAnalytics(analyticsPeriod);
    fetchEarnings();
    fetchCreatorReviews();
  }, [fetchMyListings, fetchAnalytics, fetchEarnings, fetchCreatorReviews, analyticsPeriod]);

  const handlePeriodChange = useCallback((period: string) => {
    setAnalyticsPeriod(period);
    fetchAnalytics(period);
  }, [fetchAnalytics]);

  // ── Compute summary stats ──
  const totalListings = myListings.length;
  const totalInstalls = myListings.reduce((sum, l) => sum + l.install_count, 0);
  const totalRevenue = earnings?.total_earnings_cents || 0;
  const avgRating =
    myListings.length > 0
      ? myListings.reduce((sum, l) => sum + l.rating_avg, 0) / myListings.length
      : 0;
  const pendingPayout = earnings?.pending_payout_cents || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            Creator Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Manage your marketplace agents, track sales and earnings
          </p>
        </div>
        <Link href="/marketplace">
          <AnansiButton variant="secondary" size="sm" icon={<Eye className="h-4 w-4" />}>
            Browse Marketplace
          </AnansiButton>
        </Link>
      </div>

      {/* Summary Cards */}
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Package className="h-4 w-4" />}
          label="Total Listings"
          value={String(totalListings)}
          sublabel={totalListings === 1 ? "1 published agent" : `${totalListings} published agents`}
        />
        <StatCard
          icon={<Download className="h-4 w-4" />}
          label="Total Installs"
          value={String(totalInstalls)}
          trend={totalInstalls > 0 ? "up" : null}
          sublabel={`${analytics?.total_installs || 0} in this period`}
        />
        <StatCard
          icon={<DollarSign className="h-4 w-4" />}
          label="Total Revenue"
          value={`$${(totalRevenue / 100).toFixed(2)}`}
          sublabel={earnings ? `$${(pendingPayout / 100).toFixed(2)} pending` : undefined}
          trend={totalRevenue > 0 ? "up" : null}
        />
        <StatCard
          icon={<Star className="h-4 w-4" />}
          label="Average Rating"
          value={avgRating > 0 ? avgRating.toFixed(1) : "—"}
          sublabel={myListings.reduce((s, l) => s + l.rating_count, 0) > 0
            ? `${myListings.reduce((s, l) => s + l.rating_count, 0)} reviews`
            : "No reviews yet"}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left: Listings + Chart */}
        <div className="lg:col-span-2 space-y-6">
          {/* Sales Chart */}
          <GlassCard variant="base" padding="lg" className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-[var(--color-brand-amber)]" />
                Sales
              </h2>
              <div className="flex items-center gap-1">
                {["7d", "30d", "90d", "1y"].map((p) => (
                  <button
                    key={p}
                    onClick={() => handlePeriodChange(p)}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-lg transition-colors",
                      analyticsPeriod === p
                        ? "bg-[var(--color-brand-amber)]/10 text-[var(--color-brand-amber)]"
                        : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
                    )}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>

            {analytics ? (
              <SimpleBarChart
                data={analytics.installs_over_time}
                accent="amber"
              />
            ) : (
              <div className="h-32 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-[var(--color-text-muted)]" />
              </div>
            )}

            {analytics && (
              <div className="flex items-center justify-between text-xs text-[var(--color-text-muted)] pt-2 border-t border-[var(--color-border-subtle)]">
                <span>{analytics.total_installs} installs in this period</span>
                <span>
                  ${((analytics.total_revenue_cents || 0) / 100).toFixed(2)} revenue
                </span>
              </div>
            )}
          </GlassCard>

          {/* Published Agents List */}
          <GlassCard variant="base" padding="lg" className="space-y-3">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Package className="h-5 w-5 text-[var(--color-text-muted)]" />
              Your Agents
              <span className="text-sm font-normal text-[var(--color-text-muted)]">
                ({myListings.length})
              </span>
            </h2>

            {myListings.length === 0 ? (
              <div className="text-center py-8 text-[var(--color-text-muted)]">
                <Package className="h-10 w-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">You haven&apos;t published any agents yet.</p>
                <p className="text-xs mt-1">
                  Create an agent and publish it to the marketplace.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-[var(--color-border-subtle)]">
                {myListings.map((listing) => (
                  <ListingRow key={listing.id} listing={listing} />
                ))}
              </div>
            )}
          </GlassCard>

          {/* Recent Reviews */}
          <GlassCard variant="base" padding="lg" className="space-y-3">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-[var(--color-text-muted)]" />
              Recent Reviews
              <span className="text-sm font-normal text-[var(--color-text-muted)]">
                ({creatorReviews.length})
              </span>
            </h2>

            {creatorReviews.length === 0 ? (
              <div className="text-center py-6 text-[var(--color-text-muted)]">
                <MessageSquare className="h-8 w-8 mx-auto mb-1 opacity-40" />
                <p className="text-sm">No reviews yet.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {creatorReviews.slice(0, 5).map((review) => (
                  <div
                    key={review.id}
                    className="flex items-start gap-3 py-2 border-b border-[var(--color-border-subtle)] last:border-0"
                  >
                    <div className="shrink-0">
                      <div className="flex gap-0.5">
                        {[1, 2, 3, 4, 5].map((star) => (
                          <Star
                            key={star}
                            className={cn(
                              "h-3 w-3",
                              star <= review.rating
                                ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]"
                                : "text-[var(--color-text-disabled)]"
                            )}
                          />
                        ))}
                      </div>
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-[var(--color-text-secondary)] line-clamp-2">
                        {review.review || "No written review"}
                      </p>
                      <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
                        on {review.listing_title || "Unknown listing"}
                        {review.created_at && ` · ${new Date(review.created_at).toLocaleDateString()}`}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassCard>
        </div>

        {/* Right Sidebar: Earnings & Payout */}
        <div className="space-y-4">
          {/* Earnings Summary */}
          <GlassCard variant="base" padding="lg" className="space-y-4">
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Wallet className="h-5 w-5 text-[var(--color-brand-amber)]" />
              Earnings
            </h2>

            {earnings ? (
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-[var(--color-text-muted)]">Total Earnings</p>
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {earnings.total_earnings_display}
                  </p>
                </div>

                <div className="bg-[var(--color-bg-deepest)]/40 rounded-lg p-3 space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--color-text-muted)]">Your Share (70%)</span>
                    <span className="text-[var(--color-text-primary)] font-medium">
                      ${(earnings.total_earnings_cents / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--color-text-muted)]">Platform Fee (30%)</span>
                    <span className="text-[var(--color-text-secondary)]">
                      ${(earnings.platform_fees_cents / 100).toFixed(2)}
                    </span>
                  </div>
                  <div className="h-px bg-[var(--color-border-subtle)]" />
                  <div className="flex justify-between text-xs">
                    <span className="text-amber-400 font-medium">Pending Payout</span>
                    <span className="text-amber-400 font-medium">
                      {earnings.pending_payout_display}
                    </span>
                  </div>
                </div>

                <div className="text-xs text-[var(--color-text-muted)]">
                  Revenue share: {earnings.revenue_share.creator_percentage}% creator /{" "}
                  {earnings.revenue_share.platform_percentage}% platform
                </div>
              </div>
            ) : (
              <div className="h-24 flex items-center justify-center">
                <Loader2 className="h-5 w-5 animate-spin text-[var(--color-text-muted)]" />
              </div>
            )}
          </GlassCard>

          {/* Payout History */}
          <GlassCard variant="base" padding="lg" className="space-y-3">
            <h2 className="text-base font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Clock className="h-4 w-4 text-[var(--color-text-muted)]" />
              Payout History
            </h2>

            {earnings && earnings.payout_history.length > 0 ? (
              <div className="space-y-2">
                {earnings.payout_history.map((payout) => (
                  <div
                    key={payout.id}
                    className="flex items-center justify-between py-1.5"
                  >
                    <div>
                      <p className="text-xs text-[var(--color-text-primary)]">
                        {payout.period}
                      </p>
                      <span className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full",
                        payout.status === "completed"
                          ? "bg-emerald-400/10 text-emerald-400"
                          : "bg-amber-400/10 text-amber-400"
                      )}>
                        {payout.status}
                      </span>
                    </div>
                    <span className="text-sm font-medium text-[var(--color-text-primary)]">
                      {payout.amount_display}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-[var(--color-text-muted)] py-4 text-center">
                No payout history yet
              </p>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
