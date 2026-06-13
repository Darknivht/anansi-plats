"use client";

import { cn } from "../../lib/utils";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardAction } from "../../components/ui/GlassCard";
import { BrainIcon } from "../../components/ui/BrainIcon";
import { RefreshCw, Settings, Sparkles } from "lucide-react";

interface MorningBriefingProps {
  date?: Date;
  className?: string;
  onRefresh?: () => void;
  onSettings?: () => void;
}

/**
 * Daily briefing card shown on the dashboard.
 * Displays AI-generated summary, calendar highlights, and brain stats.
 */
export function MorningBriefing({
  date = new Date(),
  className,
  onRefresh,
  onSettings,
}: MorningBriefingProps) {
  const formattedDate = date.toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <GlassCard
      variant="elevated"
      glow="amber"
      padding="lg"
      className={cn("relative overflow-hidden", className)}
    >
      {/* Subtle background gradient */}
      <div
        className="absolute inset-0 opacity-5 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse at top right, rgba(245,158,11,0.4) 0%, transparent 60%)",
        }}
      />

      <GlassCardHeader>
        <div className="flex items-center gap-3">
          <BrainIcon size={28} active glow="amber" />
          <div>
            <GlassCardTitle>Morning Briefing</GlassCardTitle>
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
              {formattedDate}
            </p>
          </div>
        </div>
        <GlassCardAction>
          <button
            onClick={onSettings}
            className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
            aria-label="Briefing settings"
            type="button"
          >
            <Settings className="h-4 w-4" />
          </button>
          <button
            onClick={onRefresh}
            className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
            aria-label="Refresh briefing"
            type="button"
          >
            <RefreshCw className="h-4 w-4" />
          </button>
        </GlassCardAction>
      </GlassCardHeader>

      <div className="space-y-4 relative z-10">
        {/* AI Suggestion */}
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/5 border border-amber-500/10">
          <Sparkles className="h-4 w-4 text-brand-amber-light shrink-0 mt-0.5" />
          <p className="text-sm text-[var(--color-text-secondary)]">
            Good morning! You have <strong className="text-[var(--color-text-primary)]">4 unread emails</strong> and{" "}
            <strong className="text-[var(--color-text-primary)]">2 overdue tasks</strong>.{" "}
            Your Second Brain grew{" "}
            <strong className="text-brand-amber-light">5 nodes</strong> and{" "}
            <strong className="text-brand-amber-light">12 links</strong> yesterday.
          </p>
        </div>

        {/* Today's Agenda */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] mb-2">
            Today's Agenda
          </h4>
          <div className="space-y-2">
            {[
              { time: "10:00 AM", event: "Design Review", type: "meeting" },
              { time: "2:00 PM", event: "Client Call — TechCo", type: "meeting" },
              { time: "4:00 PM", event: "Gym", type: "personal" },
            ].map((item) => (
              <div
                key={item.time}
                className="flex items-center gap-3 px-3 py-2 rounded-lg bg-white/5"
              >
                <div className="h-2 w-2 rounded-full bg-brand-amber-light shrink-0" />
                <span className="text-xs font-mono text-[var(--color-text-muted)] w-16">
                  {item.time}
                </span>
                <span className="text-sm text-[var(--color-text-secondary)]">
                  {item.event}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* AI Suggestion */}
        <div className="flex items-center gap-2 text-sm text-brand-amber-light/80">
          <Sparkles className="h-3.5 w-3.5" />
          <span>
            I noticed you haven&apos;t followed up with James — want me to draft an email?
          </span>
        </div>
      </div>
    </GlassCard>
  );
}
