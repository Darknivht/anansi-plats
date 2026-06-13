"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { cn } from "../../../lib/utils";
import { useIntegrationStore, type ConnectorWithStatus } from "../../../stores/integrations";
import { useUIStore } from "../../../stores/ui";
import { ConnectorCard } from "../../../components/integrations/ConnectorCard";
import { OAuthModal } from "../../../components/integrations/OAuthModal";
import { Badge } from "../../../components/ui/Badge";
import { Skeleton } from "../../../components/ui/Skeleton";

// ─── Category Config ──────────────────────────────────────────────────────

interface CategoryGroup {
  label: string;
  emoji: string;
  keys: string[];
}

const CATEGORIES: Record<string, CategoryGroup> = {
  communication: { label: "Communication", emoji: "\u{1F4AC}", keys: [] },
  productivity: { label: "Productivity", emoji: "\u{2699}\u{FE0F}", keys: [] },
  storage: { label: "Storage", emoji: "\u{1F4BE}", keys: [] },
  developer: { label: "Developer Tools", emoji: "\u{1F4BB}", keys: [] },
  finance: { label: "Finance", emoji: "\u{1F4B0}", keys: [] },
  social: { label: "Social", emoji: "\u{1F30D}", keys: [] },
};

// ─── Page ──────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const router = useRouter();
  const {
    connectors,
    statusSummary,
    error,
    isConnecting,
    fetchConnectors,
    fetchStatus,
  } = useIntegrationStore();
  const addToast = useUIStore((s) => s.addToast);

  const [selectedForAuth, setSelectedForAuth] = useState<ConnectorWithStatus | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>("all");

  // ── Load data ──
  useEffect(() => {
    fetchConnectors();
    fetchStatus();
  }, [fetchConnectors, fetchStatus]);

  // ── Handle connect click ──
  const handleConnect = useCallback(
    (connector: ConnectorWithStatus) => {
      // If connected, navigate to detail page
      if (connector.status === "connected" || connector.status === "error") {
        router.push(`/integrations/${connector.key}`);
        return;
      }
      setSelectedForAuth(connector);
    },
    [router],
  );

  // ── Filter connectors ──
  const filteredConnectors = connectors.filter((c) => {
    if (filterStatus === "all") return true;
    return c.status === filterStatus;
  });

  // ── Group by category ──
  const groupedConnectors: Record<string, ConnectorWithStatus[]> = {};
  for (const c of filteredConnectors) {
    const cat = c.category ?? "general";
    if (!groupedConnectors[cat]) groupedConnectors[cat] = [];
    groupedConnectors[cat].push(c);
  }

  // ── Summary text ──
  const connectedCount = connectors.filter((c) => c.status === "connected").length;
  const errorCount = connectors.filter((c) => c.status === "error").length;
  const availableCount = connectors.filter((c) => c.status === "disconnected").length;

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex flex-col gap-1 mb-8">
        <h1 className="text-2xl font-bold text-[var(--color-text-primary)] dark:text-white">
          Integrations
        </h1>
        <p className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50">
          Connect your services to give Anansi superpowers
        </p>
      </div>

      {/* Status Summary */}
      {statusSummary && (
        <div className="flex items-center gap-4 mb-6 flex-wrap">
          <div className="flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full bg-emerald-400" />
            <span className="text-[var(--color-text-secondary)] dark:text-white/70">
              <strong className="text-emerald-500">{statusSummary.connected}</strong> connected
            </span>
          </div>
          {statusSummary.error > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full bg-red-400" />
              <span className="text-[var(--color-text-secondary)] dark:text-white/70">
                <strong className="text-red-400">{statusSummary.error}</strong> error
              </span>
            </div>
          )}
          <div className="flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full bg-blue-400" />
            <span className="text-[var(--color-text-secondary)] dark:text-white/70">
              <strong className="text-blue-400">{statusSummary.available}</strong> available
            </span>
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        {[
          { key: "all", label: "All" },
          { key: "connected", label: "Connected" },
          { key: "error", label: "Errors" },
          { key: "disconnected", label: "Disconnected" },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilterStatus(tab.key)}
            className={cn(
              "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
              filterStatus === tab.key
                ? "bg-[var(--color-bg-cta)] text-white"
                : "bg-[var(--color-bg-elevated)] dark:bg-white/5 text-[var(--color-text-secondary)] dark:text-white/70",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {error}
          <button
            onClick={() => fetchConnectors()}
            className="ml-3 underline hover:no-underline"
          >
            Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {isConnecting && connectors.length === 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      )}

      {/* Connector Grid grouped by category */}
      {Object.entries(groupedConnectors).length > 0 ? (
        Object.entries(groupedConnectors).map(([category, items]) => {
          const catInfo = CATEGORIES[category] ?? {
            label: category.charAt(0).toUpperCase() + category.slice(1),
            emoji: "\u{1F4E6}",
            keys: [],
          };
          return (
            <div key={category} className="mb-8">
              <h2 className="text-sm font-semibold text-[var(--color-text-tertiary)] dark:text-white/40 uppercase tracking-wider mb-3 flex items-center gap-2">
                <span>{catInfo.emoji}</span>
                {catInfo.label}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {items.map((connector) => (
                  <ConnectorCard
                    key={connector.key}
                    connector={connector}
                    onConnect={handleConnect}
                  />
                ))}
              </div>
            </div>
          );
        })
      ) : (
        !isConnecting && (
          <div className="text-center py-16 text-[var(--color-text-tertiary)] dark:text-white/30">
            <p className="text-lg">No connectors found</p>
            <p className="text-sm mt-1">
              {filterStatus !== "all"
                ? `No connectors with status "${filterStatus}"`
                : "Connectors are being loaded..."}
            </p>
          </div>
        )
      )}

      {/* OAuth Modal */}
      {selectedForAuth && (
        <OAuthModal
          connector={selectedForAuth}
          onClose={() => setSelectedForAuth(null)}
          onSuccess={() => {
            fetchConnectors();
            fetchStatus();
          }}
        />
      )}
    </div>
  );
}
