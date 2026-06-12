import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
  /**
   * Number of skeleton lines to render (for text blocks)
   */
  lines?: number;
  /**
   * Variant of skeleton shape
   */
  variant?: "text" | "circular" | "rectangular" | "card";
}

/**
 * Loading skeleton with Anansi's glass shimmer effect.
 * All animations respect prefers-reduced-motion via globals.css.
 */
export function Skeleton({
  className,
  lines = 1,
  variant = "text",
}: SkeletonProps) {
  if (variant === "text") {
    return (
      <div className="flex flex-col gap-2" role="status" aria-label="Loading">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "h-4 rounded-md animate-glass-shimmer",
              i === lines - 1 && lines > 1 ? "w-3/4" : "w-full",
              className,
            )}
          />
        ))}
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (variant === "circular") {
    return (
      <div
        className={cn(
          "rounded-full animate-glass-shimmer",
          className ?? "h-10 w-10",
        )}
        role="status"
        aria-label="Loading"
      >
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  if (variant === "card") {
    return (
      <div
        className={cn(
          "rounded-lg glass-card p-4 flex flex-col gap-3",
          className,
        )}
        role="status"
        aria-label="Loading"
      >
        {/* Card header */}
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full animate-glass-shimmer" />
          <div className="flex-1 space-y-1.5">
            <div className="h-3 w-1/3 rounded animate-glass-shimmer" />
            <div className="h-2 w-1/4 rounded animate-glass-shimmer" />
          </div>
        </div>
        {/* Card body */}
        <div className="h-3 w-full rounded animate-glass-shimmer" />
        <div className="h-3 w-5/6 rounded animate-glass-shimmer" />
        <div className="h-3 w-2/3 rounded animate-glass-shimmer" />
        <span className="sr-only">Loading...</span>
      </div>
    );
  }

  // Rectangular
  return (
    <div
      className={cn(
        "rounded-lg animate-glass-shimmer",
        className ?? "h-32 w-full",
      )}
      role="status"
      aria-label="Loading"
    >
      <span className="sr-only">Loading...</span>
    </div>
  );
}
