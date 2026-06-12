"use client";

import Link from "next/link";
import { type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";

// ─── Types ─────────────────────────────────────────────────────────────────

export interface ConnectorCardData {
  key: string;
  name: string;
  description: string | null;
  iconUrl: string | null;
  category: string;
  authType: "oauth2" | "apikey" | "basic";
  status: "connected" | "disconnected" | "error" | "pending";
}

interface ConnectorCardProps {
  connector: ConnectorCardData;
  onConnect?: (connector: ConnectorCardData) => void;
  className?: string;
}

// ─── Category Icons (fallback emoji) ──────────────────────────────────────

const categoryEmoji: Record<string, string> = {
  communication: "\u{1F4AC}",
  productivity: "\u{2699}\u{FE0F}",
  storage: "\u{1F4BE}",
  developer: "\u{1F4BB}",
  finance: "\u{1F4B0}",
  social: "\u{1F30D}",
  general: "\u{1F504}",
};

// ─── Status badge configuration ───────────────────────────────────────────

const statusConfig: Record<
  string,
  { variant: "success" | "warning" | "error" | "info"; label: string }
> = {
  connected: { variant: "success", label: "Connected" },
  error: { variant: "error", label: "Error" },
  disconnected: { variant: "info", label: "Disconnected" },
  pending: { variant: "warning", label: "Connecting..." },
};

// ─── Component ────────────────────────────────────────────────────────────

export function ConnectorCard({ connector, onConnect, className }: ConnectorCardProps) {
  const { variant, label } = statusConfig[connector.status] ?? statusConfig.disconnected;
  const isConnected = connector.status === "connected";
  const hasError = connector.status === "error";

  return (
    <div
      className={cn(
        "group relative flex flex-col gap-3 rounded-xl border p-4 transition-all duration-300",
        "hover:shadow-lg hover:-translate-y-0.5",
        "bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]",
        isConnected
          ? "border-[var(--color-border-active)] dark:border-emerald-500/30"
          : hasError
          ? "border-red-500/30 dark:border-red-400/30"
          : "border-[var(--color-border)] dark:border-white/10",
        className,
      )}
    >
      {/* Status Badge */}
      <div className="absolute top-3 right-3">
        <Badge variant={variant} size="sm" pill>
          <span
            className={cn(
              "w-1.5 h-1.5 rounded-full",
              variant === "success" && "bg-emerald-400",
              variant === "error" && "bg-red-400",
              variant === "info" && "bg-blue-400",
              variant === "warning" && "bg-amber-400",
            )}
          />
          {label}
        </Badge>
      </div>

      {/* Icon / Emoji */}
      <div className="flex items-center gap-3">
        <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-[var(--color-bg-deepest)] dark:bg-white/5 flex items-center justify-center text-xl">
          {connector.iconUrl ? (
            <img
              src={connector.iconUrl}
              alt={connector.name}
              className="w-6 h-6 object-contain"
              onError={(e) => {
                // Fallback to emoji on load failure
                (e.target as HTMLImageElement).style.display = "none";
                const parent = (e.target as HTMLImageElement).parentElement;
                if (parent) {
                  parent.textContent = categoryEmoji[connector.category] ?? "\u{1F504}";
                }
              }}
            />
          ) : (
            <span>{categoryEmoji[connector.category] ?? "\u{1F504}"}</span>
          )}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-sm text-[var(--color-text-primary)] dark:text-white truncate">
            {connector.name}
          </h3>
          <p className="text-xs text-[var(--color-text-tertiary)] dark:text-white/50 truncate">
            {connector.description ?? connector.category}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-between mt-auto pt-2">
        <Link
          href={`/integrations/${connector.key}`}
          className="text-xs font-medium text-[var(--color-brand-primary)] dark:text-brand-amber hover:underline"
        >
          {isConnected ? "Manage" : "Details"}
        </Link>

        <button
          onClick={() => onConnect?.(connector)}
          className={cn(
            "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
            isConnected
              ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20"
              : "bg-[var(--color-bg-cta)] text-white hover:opacity-90",
          )}
        >
          {isConnected ? "Configure" : "Connect"}
        </button>
      </div>
    </div>
  );
}