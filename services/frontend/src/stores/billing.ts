/**
 * Billing Zustand Store — Plans, subscriptions, invoices, payment methods.
 *
 * Manages billing state: current plan, available plans, invoices, payment methods,
 * feature access checks, and usage stats.
 */

import { create } from "zustand";
import { api } from "@/lib/api";

// ─── Types ──────────────────────────────────────────────────────────────────

export interface Plan {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  price_monthly_cents: number;
  price_monthly_display: string;
  price_yearly_cents: number;
  price_yearly_display: string;
  max_agents: number | null;
  max_integrations: number | null;
  max_team_members: number | null;
  max_memory_nodes: number | null;
  max_graph_depth: number | null;
  max_reviews_per_day: number | null;
  daily_notes_history_days: number | null;
  progressive_summarization_layers: number;
  auto_linking_level: string;
  export_formats: string[];
  memory_analytics: string;
  features: Record<string, unknown>;
  sort_order: number;
  is_active: boolean;
}

export interface Subscription {
  id: string;
  status: string;
  billing_cycle: string;
  current_period_start: string | null;
  current_period_end: string | null;
  trial_end: string | null;
  canceled_at: string | null;
  stripe_subscription_id: string | null;
  paystack_subscription_code: string | null;
}

export interface CurrentPlanResponse {
  plan: Plan | null;
  subscription: Subscription | null;
  status: string;
  current_period_start: string | null;
  current_period_end: string | null;
}

export interface Invoice {
  id: string;
  amount_cents: number;
  amount_display: string;
  currency: string;
  status: string;
  period_start: string | null;
  period_end: string | null;
  paid_at: string | null;
  plan_name: string;
  billing_cycle: string;
  description: string;
}

export interface FeatureAccessResult {
  allowed: boolean;
  limit: number | null;
  current: number | null;
  plan_slug: string;
  plan_name: string;
  feature_key: string;
}

export interface UsageStats {
  agents: {
    limit: number | null;
    current: number | null;
    allowed: boolean;
  };
  integrations: {
    limit: number | null;
    current: number | null;
    allowed: boolean;
  };
  memory_nodes: {
    limit: number | null;
    current: number | null;
    allowed: boolean;
  };
  team_members: {
    limit: number | null;
    current: number | null;
    allowed: boolean;
  };
}

// ─── Store Interface ─────────────────────────────────────────────────────

interface BillingState {
  // Data
  currentPlan: CurrentPlanResponse | null;
  availablePlans: Plan[];
  invoices: Invoice[];
  usage: UsageStats | null;

  // Loading states
  isLoading: boolean;
  isUpgrading: boolean;
  error: string | null;

  // Success/feedback
  lastAction: string | null;

  // Actions
  fetchCurrentPlan: () => Promise<void>;
  fetchAvailablePlans: () => Promise<void>;
  fetchInvoices: () => Promise<void>;
  fetchUsage: () => Promise<void>;
  upgradePlan: (
    planSlug: string,
    billingCycle?: string,
    paymentMethodId?: string,
  ) => Promise<boolean>;
  downgradePlan: () => Promise<boolean>;
  cancelSubscription: () => Promise<boolean>;
  updatePaymentMethod: (paymentMethodId: string, provider?: string) => Promise<boolean>;
  checkFeatureAccess: (featureKey: string) => Promise<FeatureAccessResult>;
  clearError: () => void;
}

// ─── Store ─────────────────────────────────────────────────────────────

export const useBillingStore = create<BillingState>((set, get) => ({
  // ── State ──
  currentPlan: null,
  availablePlans: [],
  invoices: [],
  usage: null,
  isLoading: false,
  isUpgrading: false,
  error: null,
  lastAction: null,

  // ── Actions ──

  fetchCurrentPlan: async () => {
    set({ isLoading: true, error: null });

    try {
      const data = await api.get<CurrentPlanResponse>("/api/v1/billing/plan");
      set({ currentPlan: data, isLoading: false, lastAction: "fetch_plan" });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to load plan";
      set({ isLoading: false, error: message });
    }
  },

  fetchAvailablePlans: async () => {
    try {
      const data = await api.get<Plan[]>("/api/v1/billing/plans");
      set({ availablePlans: data });
    } catch {
      // Non-critical
    }
  },

  fetchInvoices: async () => {
    try {
      const data = await api.get<Invoice[]>("/api/v1/billing/invoices");
      set({ invoices: data });
    } catch {
      // Non-critical
    }
  },

  fetchUsage: async () => {
    try {
      const data = await api.get<UsageStats>("/api/v1/billing/usage");
      set({ usage: data });
    } catch {
      // Non-critical
    }
  },

  upgradePlan: async (planSlug: string, billingCycle = "monthly", paymentMethodId?: string) => {
    set({ isUpgrading: true, error: null });

    try {
      const body: Record<string, unknown> = {
        plan_slug: planSlug,
        billing_cycle: billingCycle,
      };
      if (paymentMethodId) {
        body.payment_method_id = paymentMethodId;
      }

      const data = await api.post<CurrentPlanResponse>("/api/v1/billing/upgrade", body);
      set({
        currentPlan: data,
        isUpgrading: false,
        lastAction: `upgrade_to_${planSlug}`,
      });

      // Refresh available plans and usage
      get().fetchAvailablePlans();
      get().fetchUsage();

      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to upgrade plan";
      set({ isUpgrading: false, error: message });
      return false;
    }
  },

  downgradePlan: async () => {
    set({ isUpgrading: true, error: null });

    try {
      const data = await api.post<CurrentPlanResponse>("/api/v1/billing/downgrade");
      set({
        currentPlan: data,
        isUpgrading: false,
        lastAction: "downgrade_to_free",
      });
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to downgrade plan";
      set({ isUpgrading: false, error: message });
      return false;
    }
  },

  cancelSubscription: async () => {
    set({ isUpgrading: true, error: null });

    try {
      const data = await api.post<CurrentPlanResponse>("/api/v1/billing/cancel");
      set({
        currentPlan: data,
        isUpgrading: false,
        lastAction: "cancel_subscription",
      });
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to cancel subscription";
      set({ isUpgrading: false, error: message });
      return false;
    }
  },

  updatePaymentMethod: async (paymentMethodId: string, provider = "stripe") => {
    set({ isUpgrading: true, error: null });

    try {
      await api.post("/api/v1/billing/payment-method", {
        payment_method_id: paymentMethodId,
        provider,
      });
      set({ isUpgrading: false, lastAction: "update_payment_method" });
      return true;
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to update payment method";
      set({ isUpgrading: false, error: message });
      return false;
    }
  },

  checkFeatureAccess: async (featureKey: string) => {
    try {
      const data = await api.post<FeatureAccessResult>("/api/v1/billing/check-feature", {
        feature_key: featureKey,
      });
      return data;
    } catch {
      return {
        allowed: false,
        limit: null,
        current: null,
        plan_slug: "free",
        plan_name: "Free",
        feature_key: featureKey,
      };
    }
  },

  clearError: () => set({ error: null }),
}));
