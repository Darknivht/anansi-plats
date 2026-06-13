"use client";

import { cn } from "../../lib/utils";
import { AnansiButton } from "../../components/ui/AnansiButton";
import { GlassCard } from "../../components/ui/GlassCard";
import { Check, X, Sparkles, Zap, Building2 } from "lucide-react";
import type { Plan } from "../../stores/billing";

// ─── Plan Feature Item ───────────────────────────────────────────────────────

function PlanFeature({
  label,
  available,
  value,
}: {
  label: string;
  available: boolean;
  value?: string | number | null;
}) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {available ? (
        <Check className="h-4 w-4 text-emerald-400 shrink-0" />
      ) : (
        <X className="h-4 w-4 text-[var(--color-text-disabled)] shrink-0" />
      )}
      <span
        className={cn(
          available
            ? "text-[var(--color-text-primary)]"
            : "text-[var(--color-text-disabled)]"
        )}
      >
        {label}
        {value !== null && value !== undefined && (
          <span className="text-[var(--color-text-muted)] ml-1">
            ({value})
          </span>
        )}
      </span>
    </div>
  );
}

// ─── Plan Card ───────────────────────────────────────────────────────────────

interface PlanCardProps {
  plan: Plan;
  isCurrentPlan?: boolean;
  onUpgrade?: (planSlug: string) => void;
  onDowngrade?: () => void;
  isLoading?: boolean;
}

const planIcons: Record<string, React.ReactNode> = {
  free: <Sparkles className="h-8 w-8 text-[var(--color-text-muted)]" />,
  pro: <Zap className="h-8 w-8 text-[var(--color-brand-amber)]" />,
  business: <Building2 className="h-8 w-8 text-[var(--color-spirit-violet)]" />,
};

const planGradients: Record<string, string> = {
  free: "from-[var(--color-text-muted)]/10 to-transparent",
  pro: "from-[var(--color-brand-amber)]/10 to-[var(--color-brand-amber)]/5",
  business: "from-[var(--color-spirit-violet)]/10 to-[var(--color-spirit-violet)]/5",
};

export function PlanCard({
  plan,
  isCurrentPlan = false,
  onUpgrade,
  onDowngrade,
  isLoading = false,
}: PlanCardProps) {
  const isFree = plan.slug === "free";
  const monthlyPrice = plan.price_monthly_cents;

  return (
    <GlassCard
      variant={isCurrentPlan ? "elevated" : "base"}
      glow={isCurrentPlan ? "amber" : undefined}
      padding="lg"
      className={cn(
        "relative overflow-hidden transition-all duration-300",
        isCurrentPlan && "ring-1 ring-[var(--color-brand-amber)]/30",
        !isCurrentPlan && "hover:translate-y-[-2px] hover:shadow-lg"
      )}
    >
      {/* Background gradient */}
      <div
        className={cn(
          "absolute inset-0 bg-gradient-to-b opacity-30",
          planGradients[plan.slug] || "from-white/5 to-transparent"
        )}
      />

      {/* Current plan badge */}
      {isCurrentPlan && (
        <div className="absolute top-3 right-3">
          <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-brand-amber)] bg-[var(--color-brand-amber)]/10 px-2 py-0.5 rounded-full">
            Current
          </span>
        </div>
      )}

      <div className="relative space-y-4">
        {/* Icon + Name */}
        <div className="flex items-center gap-3">
          {planIcons[plan.slug] || <Sparkles className="h-8 w-8" />}
          <div>
            <h3 className="text-lg font-bold text-[var(--color-text-primary)]">
              {plan.name}
            </h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              {plan.description || ""}
            </p>
          </div>
        </div>

        {/* Price */}
        <div>
          <span className="text-3xl font-extrabold text-[var(--color-text-primary)]">
            {monthlyPrice === 0 ? "Free" : `$${(monthlyPrice / 100).toFixed(0)}`}
          </span>
          {monthlyPrice > 0 && (
            <span className="text-sm text-[var(--color-text-muted)] ml-1">/mo</span>
          )}
        </div>

        {/* Features */}
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
            Features
          </p>
          <PlanFeature
            label="AI Agents"
            available={plan.max_agents !== 0}
            value={plan.max_agents === null ? "Unlimited" : plan.max_agents}
          />
          <PlanFeature
            label="Integrations"
            available={plan.max_integrations !== 0}
            value={plan.max_integrations === null ? "Unlimited" : plan.max_integrations}
          />
          <PlanFeature
            label="Memory Nodes"
            available={plan.max_memory_nodes !== 0}
            value={plan.max_memory_nodes === null ? "Unlimited" : plan.max_memory_nodes?.toLocaleString()}
          />
          <PlanFeature
            label="Team Members"
            available={(plan.max_team_members || 0) > 1}
            value={plan.max_team_members}
          />
          <PlanFeature
            label="Daily Notes History"
            available={(plan.daily_notes_history_days || 0) > 7}
            value={plan.daily_notes_history_days ? `${plan.daily_notes_history_days} days` : "7 days"}
          />
          <PlanFeature
            label="Progressive Summarization"
            available={plan.progressive_summarization_layers > 1}
            value={`${plan.progressive_summarization_layers} layers`}
          />
          <PlanFeature
            label="Auto-linking"
            available={plan.auto_linking_level !== "none"}
            value={plan.auto_linking_level}
          />
          <PlanFeature
            label="Memory Analytics"
            available={plan.memory_analytics !== "none"}
            value={plan.memory_analytics}
          />
          <PlanFeature
            label="Graph View Depth"
            available={(plan.max_graph_depth || 0) >= 3}
            value={plan.max_graph_depth ? `level ${plan.max_graph_depth}` : "level 2"}
          />
          <PlanFeature
            label="Private Marketplace"
            available={!!plan.features?.private_marketplace}
          />
        </div>

        {/* Action Button */}
        <div className="pt-2">
          {isCurrentPlan ? (
            <AnansiButton
              variant="secondary"
              size="md"
              fullWidth
              disabled
            >
              Current Plan
            </AnansiButton>
          ) : isFree ? (
            <AnansiButton
              variant="ghost"
              size="md"
              fullWidth
              onClick={onDowngrade}
              disabled={isLoading}
            >
              Downgrade
            </AnansiButton>
          ) : (
            <AnansiButton
              variant="primary"
              size="md"
              fullWidth
              icon={<Sparkles className="h-4 w-4" />}
              onClick={() => onUpgrade?.(plan.slug)}
              disabled={isLoading}
            >
              Upgrade to {plan.name}
            </AnansiButton>
          )}
        </div>
      </div>
    </GlassCard>
  );
}

// ─── Exports ─────────────────────────────────────────────────────────────────

export { PlanFeature };
