"use client";

import { cn } from "@/lib/utils";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { GlassCard } from "@/components/ui/GlassCard";
import { Check, X, Sparkles, Zap, Building2 } from "lucide-react";
import type { Plan } from "@/stores/billing";

// ─── Plan Comparison Table ───────────────────────────────────────────────────

interface PlanComparisonProps {
  plans: Plan[];
  currentPlanSlug?: string;
  onSelectPlan: (planSlug: string) => void;
  isLoading?: boolean;
}

const planIcons: Record<string, React.ReactNode> = {
  free: null,
  pro: <Zap className="h-4 w-4 text-[var(--color-brand-amber)]" />,
  business: <Building2 className="h-4 w-4 text-[var(--color-spirit-violet)]" />,
};

export function PlanComparison({
  plans,
  currentPlanSlug = "free",
  onSelectPlan,
  isLoading = false,
}: PlanComparisonProps) {
  // Features to compare
  const featureRows: {
    label: string;
    getValue: (plan: Plan) => { available: boolean; display: string };
  }[] = [
    {
      label: "AI Agents",
      getValue: (p) => ({
        available: p.max_agents !== 0,
        display: p.max_agents === null ? "Unlimited" : String(p.max_agents),
      }),
    },
    {
      label: "Integrations",
      getValue: (p) => ({
        available: p.max_integrations !== 0,
        display: p.max_integrations === null ? "Unlimited" : String(p.max_integrations),
      }),
    },
    {
      label: "Memory Nodes",
      getValue: (p) => ({
        available: p.max_memory_nodes !== 0,
        display: p.max_memory_nodes === null
          ? "Unlimited"
          : p.max_memory_nodes >= 1000
            ? `${(p.max_memory_nodes / 1000).toFixed(0)}K`
            : String(p.max_memory_nodes),
      }),
    },
    {
      label: "Team Members",
      getValue: (p) => ({
        available: (p.max_team_members || 0) > 1,
        display: String(p.max_team_members || 1),
      }),
    },
    {
      label: "Daily History",
      getValue: (p) => ({
        available: (p.daily_notes_history_days || 7) > 7,
        display: p.daily_notes_history_days ? `${p.daily_notes_history_days}d` : "7d",
      }),
    },
    {
      label: "Summarization Layers",
      getValue: (p) => ({
        available: p.progressive_summarization_layers > 1,
        display: String(p.progressive_summarization_layers),
      }),
    },
    {
      label: "Auto-linking",
      getValue: (p) => ({
        available: p.auto_linking_level !== "basic",
        display: p.auto_linking_level,
      }),
    },
    {
      label: "Analytics",
      getValue: (p) => ({
        available: p.memory_analytics !== "weekly",
        display: p.memory_analytics,
      }),
    },
    {
      label: "Graph Depth",
      getValue: (p) => ({
        available: (p.max_graph_depth || 2) >= 3,
        display: `L${p.max_graph_depth || 2}`,
      }),
    },
    {
      label: "Export Formats",
      getValue: (p) => ({
        available: p.export_formats.length > 2,
        display: p.export_formats.length > 0
          ? p.export_formats.join(", ").toUpperCase()
          : "CSV, JSON",
      }),
    },
    {
      label: "Private Marketplace",
      getValue: (p) => ({
        available: !!p.features?.private_marketplace,
        display: !!p.features?.private_marketplace ? "Yes" : "No",
      }),
    },
  ];

  return (
    <GlassCard variant="base" padding="lg" className="overflow-x-auto">
      <table className="w-full text-sm">
        {/* Header */}
        <thead>
          <tr>
            <th className="text-left py-3 pr-4 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] w-[180px]">
              Feature
            </th>
            {plans.map((plan) => {
              const isCurrent = plan.slug === currentPlanSlug;
              return (
                <th
                  key={plan.id}
                  className={cn(
                    "text-center py-3 px-4 min-w-[120px]",
                    isCurrent && "text-[var(--color-brand-amber)]"
                  )}
                >
                  <div className="flex items-center justify-center gap-1.5">
                    {planIcons[plan.slug]}
                    <span className="font-bold">{plan.name}</span>
                  </div>
                  <div className="mt-1">
                    <span className="text-lg font-extrabold">
                      {plan.price_monthly_cents === 0
                        ? "Free"
                        : `$${(plan.price_monthly_cents / 100).toFixed(0)}`}
                    </span>
                    {plan.price_monthly_cents > 0 && (
                      <span className="text-xs text-[var(--color-text-muted)]">/mo</span>
                    )}
                  </div>
                  {isCurrent && (
                    <div className="mt-1">
                      <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--color-brand-amber)]">
                        Current
                      </span>
                    </div>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>

        {/* Body */}
        <tbody>
          {featureRows.map((row, idx) => (
            <tr
              key={row.label}
              className={cn(
                "border-t border-[var(--color-border-subtle)]",
                idx % 2 === 0 && "bg-white/[0.02]"
              )}
            >
              <td className="py-3 pr-4 text-[var(--color-text-secondary)]">
                {row.label}
              </td>
              {plans.map((plan) => {
                const { available, display } = row.getValue(plan);
                const isCurrent = plan.slug === currentPlanSlug;
                return (
                  <td
                    key={plan.id}
                    className={cn(
                      "text-center py-3 px-4",
                      isCurrent && "text-[var(--color-brand-amber)]"
                    )}
                  >
                    <div className="flex items-center justify-center gap-1.5">
                      {available ? (
                        <Check className="h-4 w-4 text-emerald-400 shrink-0" />
                      ) : (
                        <X className="h-4 w-4 text-[var(--color-text-disabled)] shrink-0" />
                      )}
                      <span
                        className={cn(
                          "text-xs",
                          available
                            ? "text-[var(--color-text-primary)]"
                            : "text-[var(--color-text-disabled)]"
                        )}
                      >
                        {display}
                      </span>
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>

        {/* Actions */}
        <tfoot>
          <tr>
            <td className="py-4 pr-4" />
            {plans.map((plan) => {
              const isCurrent = plan.slug === currentPlanSlug;
              return (
                <td key={plan.id} className="text-center py-4 px-4">
                  {isCurrent ? (
                    <AnansiButton variant="secondary" size="sm" disabled>
                      Current
                    </AnansiButton>
                  ) : plan.slug === "free" ? (
                    <AnansiButton
                      variant="ghost"
                      size="sm"
                      onClick={() => onSelectPlan(plan.slug)}
                      disabled={isLoading}
                    >
                      Downgrade
                    </AnansiButton>
                  ) : (
                    <AnansiButton
                      variant="primary"
                      size="sm"
                      onClick={() => onSelectPlan(plan.slug)}
                      disabled={isLoading}
                    >
                      Upgrade
                    </AnansiButton>
                  )}
                </td>
              );
            })}
          </tr>
        </tfoot>
      </table>
    </GlassCard>
  );
}
