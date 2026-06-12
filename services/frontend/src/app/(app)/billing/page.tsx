"use client";

import { useEffect, useState, useCallback } from "react";
import { useBillingStore, type Plan } from "@/stores/billing";
import { PlanCard } from "@/components/billing/PlanCard";
import { PlanComparison } from "@/components/billing/PlanComparison";
import { GlassCard } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  CreditCard,
  FileText,
  Check,
  X,
  AlertCircle,
  Loader2,
  Shield,
  CircleDot,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

// ─── Usage Bar ───────────────────────────────────────────────────────────────

function UsageBar({
  label,
  current,
  limit,
  icon,
}: {
  label: string;
  current: number | null;
  limit: number | null;
  icon: React.ReactNode;
}) {
  const percentage = limit && limit > 0 ? Math.min(((current || 0) / limit) * 100, 100) : 0;
  const isNearLimit = percentage >= 80;
  const isAtLimit = percentage >= 100;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-1.5 text-[var(--color-text-muted)]">
          {icon}
          <span>{label}</span>
        </div>
        <span className={cn(
          "font-medium",
          isAtLimit ? "text-red-400" : isNearLimit ? "text-amber-400" : "text-[var(--color-text-primary)]"
        )}>
          {current ?? 0} / {limit ?? "∞"}
        </span>
      </div>
      {limit && limit > 0 && (
        <div className="w-full h-1.5 bg-[var(--color-bg-deepest)] rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full rounded-full transition-all duration-500",
              isAtLimit
                ? "bg-red-500"
                : isNearLimit
                  ? "bg-amber-500"
                  : "bg-[var(--color-brand-amber)]"
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
      )}
    </div>
  );
}

// ─── Invoice Row ─────────────────────────────────────────────────────────────

function InvoiceRow({ invoice }: { invoice: import("@/stores/billing").Invoice }) {
  const dateStr = invoice.period_start
    ? new Date(invoice.period_start).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "";

  const isPaid = invoice.status === "paid";

  return (
    <div className="flex items-center justify-between py-3 border-b border-[var(--color-border-subtle)] last:border-0">
      <div className="flex items-center gap-3">
        <div className={cn(
          "h-8 w-8 rounded-lg flex items-center justify-center",
          isPaid ? "bg-emerald-400/10" : "bg-amber-400/10"
        )}>
          <FileText className={cn(
            "h-4 w-4",
            isPaid ? "text-emerald-400" : "text-amber-400"
          )} />
        </div>
        <div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">
            {invoice.description}
          </p>
          <p className="text-xs text-[var(--color-text-muted)]">{dateStr}</p>
        </div>
      </div>
      <div className="text-right">
        <p className="text-sm font-semibold text-[var(--color-text-primary)]">
          {invoice.amount_display}
        </p>
        <span className={cn(
          "text-[10px] px-1.5 py-0.5 rounded-full",
          isPaid
            ? "bg-emerald-400/10 text-emerald-400"
            : "bg-amber-400/10 text-amber-400"
        )}>
          {isPaid ? "Paid" : "Pending"}
        </span>
      </div>
    </div>
  );
}

// ─── Payment Method Card ─────────────────────────────────────────────────────

function PaymentMethodSection({
  hasCard,
  onUpdate,
  isUpdating,
}: {
  hasCard: boolean;
  onUpdate: () => void;
  isUpdating: boolean;
}) {
  return (
    <GlassCard variant="base" padding="lg" className="space-y-4">
      <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
        <CreditCard className="h-5 w-5 text-[var(--color-text-muted)]" />
        Payment Method
      </h2>

      {hasCard ? (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-14 rounded-lg bg-gradient-to-br from-blue-500/20 to-purple-500/20 flex items-center justify-center">
              <CreditCard className="h-5 w-5 text-[var(--color-text-muted)]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[var(--color-text-primary)]">
                Visa ending in 4242
              </p>
              <p className="text-xs text-[var(--color-text-muted)]">
                Expires 12/28
              </p>
            </div>
          </div>
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={onUpdate}
            disabled={isUpdating}
          >
            Update
          </AnansiButton>
        </div>
      ) : (
        <div className="text-center py-4 space-y-2">
          <CreditCard className="h-8 w-8 mx-auto text-[var(--color-text-disabled)]" />
          <p className="text-sm text-[var(--color-text-muted)]">
            No payment method on file
          </p>
          <AnansiButton
            variant="secondary"
            size="sm"
            onClick={onUpdate}
            disabled={isUpdating}
          >
            Add Payment Method
          </AnansiButton>
        </div>
      )}
    </GlassCard>
  );
}

// ─── Billing Page ────────────────────────────────────────────────────────────

export default function BillingPage() {
  const {
    currentPlan,
    availablePlans,
    invoices,
    usage,
    isLoading,
    isUpgrading,
    error,
    lastAction,
    fetchCurrentPlan,
    fetchAvailablePlans,
    fetchInvoices,
    fetchUsage,
    upgradePlan,
    downgradePlan,
    updatePaymentMethod,
    clearError,
  } = useBillingStore();

  const [showComparison, setShowComparison] = useState(false);
  const [upgradeModal, setUpgradeModal] = useState<string | null>(null);

  useEffect(() => {
    fetchCurrentPlan();
    fetchAvailablePlans();
    fetchInvoices();
    fetchUsage();
  }, [fetchCurrentPlan, fetchAvailablePlans, fetchInvoices, fetchUsage]);

  const handleUpgrade = useCallback(
    async (planSlug: string) => {
      const success = await upgradePlan(planSlug);
      if (success) {
        setUpgradeModal(null);
        fetchInvoices();
        fetchUsage();
      }
    },
    [upgradePlan, fetchInvoices, fetchUsage]
  );

  const handleDowngrade = useCallback(async () => {
    const success = await downgradePlan();
    if (success) {
      fetchAvailablePlans();
      fetchInvoices();
      fetchUsage();
    }
  }, [downgradePlan, fetchAvailablePlans, fetchInvoices, fetchUsage]);

  const handleUpdatePayment = useCallback(async () => {
    // In production, this would open Stripe Elements or Paystack popup
    await updatePaymentMethod("pm_demo", "stripe");
  }, [updatePaymentMethod]);

  const currentPlanSlug = currentPlan?.plan?.slug || "free";
  const planStatus = currentPlan?.status || "free";
  const isOnPaidPlan = currentPlanSlug !== "free" && planStatus === "active";

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            Billing & Plan
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Manage your subscription, usage, and payment methods
          </p>
        </div>
        <Shield className="h-8 w-8 text-[var(--color-deep-teal)]" />
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3">
          <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
          <p className="text-sm text-red-300 flex-1">{error}</p>
          <button onClick={clearError} className="text-xs text-red-400 hover:text-red-300">
            Dismiss
          </button>
        </div>
      )}

      {/* Current Plan Card */}
      {isLoading ? (
        <Skeleton className="w-full h-40 rounded-xl" />
      ) : currentPlan?.plan ? (
        <GlassCard variant="elevated" glow="amber" padding="lg" className="space-y-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)]">
                Current Plan
              </p>
              <h2 className="text-2xl font-bold text-[var(--color-text-primary)] mt-1">
                {currentPlan.plan.name}
              </h2>
              <div className="flex items-center gap-3 mt-1 text-sm text-[var(--color-text-muted)]">
                <span>
                  {currentPlan.plan.price_monthly_cents === 0
                    ? "Free"
                    : `$${(currentPlan.plan.price_monthly_cents / 100).toFixed(0)}/mo`}
                </span>
                <CircleDot className="h-1.5 w-1.5" />
                <span className={cn(
                  planStatus === "active" || planStatus === "free"
                    ? "text-emerald-400"
                    : planStatus === "past_due"
                      ? "text-red-400"
                      : "text-amber-400"
                )}>
                  {planStatus === "active" || planStatus === "free" ? "Active"
                    : planStatus === "cancelled" ? "Cancelled"
                    : "Past Due"}
                </span>
                {currentPlan.subscription?.current_period_end && (
                  <>
                    <CircleDot className="h-1.5 w-1.5" />
                    <span>
                      Renews{" "}
                      {new Date(currentPlan.subscription.current_period_end).toLocaleDateString(
                        "en-US",
                        { month: "short", day: "numeric", year: "numeric" }
                      )}
                    </span>
                  </>
                )}
              </div>
            </div>

            {isOnPaidPlan ? (
              <AnansiButton
                variant="ghost"
                size="sm"
                onClick={handleDowngrade}
                disabled={isUpgrading}
              >
                Cancel Subscription
              </AnansiButton>
            ) : currentPlanSlug === "free" ? null : (
              <span className="text-xs text-amber-400">
                Cancelled — active until period end
              </span>
            )}
          </div>

          {/* Feature summary chips */}
          <div className="flex flex-wrap gap-2">
            {currentPlan.plan.max_agents && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                {currentPlan.plan.max_agents} Agents
              </span>
            )}
            {currentPlan.plan.max_integrations && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                {currentPlan.plan.max_integrations} Integrations
              </span>
            )}
            {currentPlan.plan.max_team_members && currentPlan.plan.max_team_members > 1 && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                {currentPlan.plan.max_team_members} Team Members
              </span>
            )}
            {currentPlan.plan.max_memory_nodes && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                {currentPlan.plan.max_memory_nodes.toLocaleString()} Memory Nodes
              </span>
            )}
            {currentPlan.plan.progressive_summarization_layers > 1 && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                {currentPlan.plan.progressive_summarization_layers} Layers
              </span>
            )}
            {!!currentPlan.plan.features?.private_marketplace && (
              <span className="text-xs bg-[var(--color-bg-deepest)] text-[var(--color-text-secondary)] px-2.5 py-1 rounded-full">
                Private Marketplace
              </span>
            )}
          </div>
        </GlassCard>
      ) : null}

      {/* Usage Stats */}
      {usage && (
        <GlassCard variant="base" padding="lg" className="space-y-3">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Usage This Month
          </h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <UsageBar
              label="Agents"
              current={usage.agents.current}
              limit={usage.agents.limit}
              icon={<CircleDot className="h-3 w-3" />}
            />
            <UsageBar
              label="Integrations"
              current={usage.integrations.current}
              limit={usage.integrations.limit}
              icon={<CircleDot className="h-3 w-3" />}
            />
            <UsageBar
              label="Memory Nodes"
              current={usage.memory_nodes.current}
              limit={usage.memory_nodes.limit}
              icon={<CircleDot className="h-3 w-3" />}
            />
            <UsageBar
              label="Team Members"
              current={usage.team_members.current}
              limit={usage.team_members.limit}
              icon={<CircleDot className="h-3 w-3" />}
            />
          </div>
        </GlassCard>
      )}

      {/* Plan Cards Visual */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[var(--color-text-primary)]">
            Available Plans
          </h2>
          <button
            onClick={() => setShowComparison(!showComparison)}
            className="flex items-center gap-1 text-xs text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            {showComparison ? "Hide" : "Show"} comparison
            {showComparison ? (
              <ChevronUp className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
          </button>
        </div>

        {/* Plan Cards Grid */}
        <div className="grid md:grid-cols-3 gap-4">
          {availablePlans.map((plan) => (
            <PlanCard
              key={plan.id}
              plan={plan}
              isCurrentPlan={plan.slug === currentPlanSlug}
              onUpgrade={handleUpgrade}
              onDowngrade={handleDowngrade}
              isLoading={isUpgrading}
            />
          ))}
        </div>

        {/* Comparison Table */}
        {showComparison && (
          <PlanComparison
            plans={availablePlans}
            currentPlanSlug={currentPlanSlug}
            onSelectPlan={handleUpgrade}
            isLoading={isUpgrading}
          />
        )}
      </div>

      {/* Payment Method */}
      <PaymentMethodSection
        hasCard={isOnPaidPlan}
        onUpdate={handleUpdatePayment}
        isUpdating={isUpgrading}
      />

      {/* Invoice History */}
      <GlassCard variant="base" padding="lg" className="space-y-3">
        <h2 className="text-lg font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
          <FileText className="h-5 w-5 text-[var(--color-text-muted)]" />
          Invoice History
        </h2>

        {invoices.length === 0 ? (
          <div className="text-center py-6 text-[var(--color-text-muted)]">
            <FileText className="h-8 w-8 mx-auto mb-1 opacity-40" />
            <p className="text-sm">No invoices yet.</p>
            <p className="text-xs mt-0.5">Invoices appear after your first payment.</p>
          </div>
        ) : (
          <div>
            {invoices.map((invoice) => (
              <InvoiceRow key={invoice.id} invoice={invoice} />
            ))}
          </div>
        )}
      </GlassCard>

      {/* Loading overlay for upgrades */}
      {isUpgrading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <GlassCard variant="elevated" padding="lg" className="text-center space-y-3">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-[var(--color-brand-amber)]" />
            <p className="text-sm text-[var(--color-text-primary)]">
              Processing your plan change...
            </p>
            <p className="text-xs text-[var(--color-text-muted)]">
              Please wait while we update your subscription.
            </p>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
