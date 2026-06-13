"use client";

import { useState, useCallback } from "react";
import { cn } from "../../lib/utils";
import { AnansiButton } from "../../components/ui/AnansiButton";
import { GlassCard } from "../../components/ui/GlassCard";
import { Star, MessageSquare, User, Loader2 } from "lucide-react";
import type { MarketplaceReview } from "../../stores/marketplace";

// ─── Interactive Star Rating Input ───────────────────────────────────────────

function StarRatingInput({
  value,
  onChange,
  disabled = false,
}: {
  value: number;
  onChange: (rating: number) => void;
  disabled?: boolean;
}) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= (hovered || value);
        return (
          <button
            key={star}
            type="button"
            disabled={disabled}
            className={cn(
              "transition-all duration-150",
              disabled ? "cursor-not-allowed opacity-50" : "cursor-pointer hover:scale-110",
            )}
            onMouseEnter={() => !disabled && setHovered(star)}
            onMouseLeave={() => !disabled && setHovered(0)}
            onClick={() => onChange(star)}
            aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
          >
            <Star
              className={cn(
                "h-6 w-6",
                filled
                  ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]"
                  : "text-[var(--color-text-disabled)]"
              )}
            />
          </button>
        );
      })}
    </div>
  );
}

// ─── Single Review Display ───────────────────────────────────────────────────

function ReviewCard({ review }: { review: MarketplaceReview }) {
  const dateStr = review.created_at
    ? new Date(review.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "";

  return (
    <div className="py-4 border-b border-[var(--color-border-subtle)] last:border-0">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-[var(--color-brand-amber)]/30 to-[var(--color-spirit-violet)]/30 flex items-center justify-center">
            <User className="h-4 w-4 text-[var(--color-text-muted)]" />
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--color-text-primary)]">
              {review.reviewer_name || "Anonymous"}
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">{dateStr}</p>
          </div>
        </div>
        {/* Static star display */}
        <div className="flex items-center gap-0.5">
          {[1, 2, 3, 4, 5].map((star) => (
            <Star
              key={star}
              className={cn(
                "h-3.5 w-3.5",
                star <= review.rating
                  ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]"
                  : "text-[var(--color-text-disabled)]"
              )}
            />
          ))}
        </div>
      </div>
      {review.review && (
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {review.review}
        </p>
      )}
    </div>
  );
}

// ─── Review Section ──────────────────────────────────────────────────────────

interface ReviewSectionProps {
  reviews: MarketplaceReview[];
  listingId: string;
  currentUserId?: string;
  onSubmitReview: (rating: number, review?: string) => Promise<void>;
  isSubmitting?: boolean;
  isAuthenticated?: boolean;
}

export function ReviewSection({
  reviews,
  listingId,
  currentUserId,
  onSubmitReview,
  isSubmitting = false,
  isAuthenticated = false,
}: ReviewSectionProps) {
  const [showForm, setShowForm] = useState(false);
  const [rating, setRating] = useState(0);
  const [reviewText, setReviewText] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Check if user has already reviewed
  const userReview = reviews.find((r) => r.user_id === currentUserId);

  const handleSubmit = useCallback(async () => {
    if (rating === 0) {
      setError("Please select a rating");
      return;
    }
    setError(null);
    await onSubmitReview(rating, reviewText.trim() || undefined);
    setShowForm(false);
    setRating(0);
    setReviewText("");
  }, [rating, reviewText, onSubmitReview]);

  const avgRating =
    reviews.length > 0
      ? reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length
      : 0;

  return (
    <GlassCard variant="base" padding="lg" className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-[var(--color-brand-amber)]" />
          <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
            Reviews
          </h3>
          <span className="text-sm text-[var(--color-text-muted)]">
            ({reviews.length})
          </span>
        </div>

        {isAuthenticated && !showForm && (
          <AnansiButton
            variant="secondary"
            size="sm"
            onClick={() => setShowForm(true)}
          >
            {userReview ? "Edit Review" : "Write Review"}
          </AnansiButton>
        )}
      </div>

      {/* Average rating summary */}
      {reviews.length > 0 && (
        <div className="flex items-center gap-3 pb-2">
          <span className="text-2xl font-bold text-[var(--color-text-primary)]">
            {avgRating.toFixed(1)}
          </span>
          <div className="flex items-center gap-0.5">
            {[1, 2, 3, 4, 5].map((star) => (
              <Star
                key={star}
                className={cn(
                  "h-4 w-4",
                  star <= Math.round(avgRating)
                    ? "text-[var(--color-brand-amber)] fill-[var(--color-brand-amber)]"
                    : "text-[var(--color-text-disabled)]"
                )}
              />
            ))}
          </div>
          <span className="text-sm text-[var(--color-text-muted)]">
            {reviews.length} review{reviews.length !== 1 ? "s" : ""}
          </span>
        </div>
      )}

      {/* Empty state */}
      {reviews.length === 0 && !showForm && (
        <div className="text-center py-8 text-[var(--color-text-muted)]">
          <MessageSquare className="h-10 w-10 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No reviews yet. Be the first to review!</p>
        </div>
      )}

      {/* Review Form */}
      {showForm && (
        <div className="bg-[var(--color-bg-surface)]/40 rounded-lg p-4 space-y-3">
          <p className="text-sm font-medium text-[var(--color-text-primary)]">
            {userReview ? "Update your review" : "Write a review"}
          </p>
          <StarRatingInput
            value={rating || userReview?.rating || 0}
            onChange={setRating}
            disabled={isSubmitting}
          />
          <textarea
            className={cn(
              "w-full min-h-[80px] px-3 py-2 rounded-lg text-sm",
              "bg-[var(--color-bg-deepest)] border border-[var(--color-border-subtle)]",
              "text-[var(--color-text-primary)] placeholder:text-[var(--color-text-disabled)]",
              "focus:outline-none focus:border-[var(--color-brand-amber)]/50 focus:ring-1 focus:ring-[var(--color-brand-amber)]/20",
              "transition-colors resize-none"
            )}
            placeholder="Share your experience with this agent..."
            value={reviewText}
            onChange={(e) => setReviewText(e.target.value)}
            disabled={isSubmitting}
          />
          {error && (
            <p className="text-xs text-red-400">{error}</p>
          )}
          <div className="flex items-center gap-2">
            <AnansiButton
              variant="primary"
              size="sm"
              onClick={handleSubmit}
              disabled={isSubmitting}
              feedbackState={isSubmitting ? "loading" : "idle"}
            >
              {isSubmitting ? "Submitting..." : userReview ? "Update" : "Submit"}
            </AnansiButton>
            <AnansiButton
              variant="ghost"
              size="sm"
              onClick={() => {
                setShowForm(false);
                setError(null);
                setRating(0);
                setReviewText("");
              }}
              disabled={isSubmitting}
            >
              Cancel
            </AnansiButton>
          </div>
        </div>
      )}

      {/* Reviews list */}
      <div className="divide-y divide-[var(--color-border-subtle)]">
        {reviews.map((review) => (
          <ReviewCard key={review.id} review={review} />
        ))}
      </div>
    </GlassCard>
  );
}
