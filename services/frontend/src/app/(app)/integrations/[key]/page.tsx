"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useIntegrationStore } from "@/stores/integrations";
import { useUIStore } from "@/stores/ui";
import { Badge } from "@/components/ui/Badge";
import { OAuthModal } from "@/components/integrations/OAuthModal";
import type { ConnectorWithStatus } from "@/stores/integrations";

// ─── Auth Type Display ────────────────────────────────────────────────────

const authTypeLabels: Record<string, { label: string; color: string }> = {
  oauth2: { label: "OAuth 2.0", color: "bg-blue-500/10 text-blue-400" },
  apikey: { label: "API Key", color: "bg-purple-500/10 text-purple-400" },
  basic: { label: "Basic Auth", color: "bg-amber-500/10 text-amber-400" },
};

// ─── Page ──────────────────────────────────────────────────────────────────

export default function ConnectorDetailPage() {
  const params = useParams();
  const router = useRouter();
  const key = params.key as string;

  const {
    connectors,
    selectedIntegration,
    fetchConnectors,
    fetchIntegrationDetail,
    disconnect,
    testConnection,
    refreshToken,
    error,
  } = useIntegrationStore();
  const addToast = useUIStore((s) => s.addToast);

  const [showOAuth, setShowOAuth] = useState(false);
  const [testing, setTesting] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  // ── Find connector ──
  const connector = connectors.find((c) => c.key === key);

  // ── Load fresh data ──
  useEffect(() => {
    if (connectors.length === 0) {
      fetchConnectors();
    }
  }, [connectors.length, fetchConnectors, key]);

  // ── Handle disconnect ──
  const handleDisconnect = useCallback(async () => {
    if (!connector?.integrationId) return;
    setDisconnecting(true);
    const success = await disconnect(connector.integrationId);
    setDisconnecting(false);
    if (success) {
      addToast("success", `${connector.name} disconnected`);
    } else {
      addToast("error", "Failed to disconnect");
    }
  }, [connector, disconnect, addToast]);

  // ── Handle test ──
  const handleTest = useCallback(async () => {
    if (!connector?.integrationId) return;
    setTesting(true);
    const result = await testConnection(connector.integrationId);
    setTesting(false);
    if (result.success) {
      addToast("success", `${connector.name} connection is healthy`);
    } else {
      addToast("error", result.error ?? "Connection test failed");
    }
  }, [connector, testConnection, addToast]);

  // ── Handle refresh ──
  const handleRefresh = useCallback(async () => {
    if (!connector?.integrationId) return;
    setRefreshing(true);
    const success = await refreshToken(connector.integrationId);
    setRefreshing(false);
    if (success) {
      addToast("success", "Token refreshed successfully");
    } else {
      addToast("error", "Token refresh failed");
    }
  }, [connector, refreshToken, addToast]);

  // ── Handle connect success ──
  const handleConnectSuccess = useCallback(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  // ── Loading / Not found ──
  if (!connector && connectors.length > 0) {
    return (
      <div className="max-w-3xl mx-auto text-center py-16">
        <p className="text-lg text-[var(--color-text-tertiary)] dark:text-white/50">
          Connector not found
        </p>
        <button
          onClick={() => router.push("/integrations")}
          className="mt-4 text-sm text-[var(--color-brand-primary)] dark:text-brand-amber hover:underline"
        >
          Back to integrations
        </button>
      </div>
    );
  }

  if (!connector) {
    return (
      <div className="max-w-3xl mx-auto animate-pulse py-8">
        <div className="h-8 w-48 bg-white/5 rounded mb-4" />
        <div className="h-4 w-96 bg-white/5 rounded" />
      </div>
    );
  }

  const isConnected = connector.status === "connected" || connector.status === "error";
  const isOAuth = connector.authType === "oauth2";
  const authInfo = authTypeLabels[connector.authType] ?? { label: connector.authType, color: "bg-gray-500/10 text-gray-400" };

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back link */}
      <button
        onClick={() => router.push("/integrations")}
        className="mb-6 text-sm text-[var(--color-text-tertiary)] dark:text-white/50 hover:text-[var(--color-text-primary)] dark:hover:text-white flex items-center gap-1"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Back to integrations
      </button>

      {/* Connector Header */}
      <div className="flex items-start gap-4 mb-8">
        <div className="w-14 h-14 rounded-xl bg-[var(--color-bg-deepest)] dark:bg-white/5 flex items-center justify-center text-2xl flex-shrink-0">
          {connector.iconUrl ? (
            <img src={connector.iconUrl} alt={connector.name} className="w-8 h-8 object-contain" />
          ) : (
            <span>{connector.name[0]}</span>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-2xl font-bold text-[var(--color-text-primary)] dark:text-white">
              {connector.name}
            </h1>
            <Badge
              variant={
                connector.status === "connected"
                  ? "success"
                  : connector.status === "error"
                  ? "error"
                  : "info"
              }
              size="sm"
              pill
            >
              <span
                className={cn(
                  "w-1.5 h-1.5 rounded-full",
                  connector.status === "connected" && "bg-emerald-400",
                  connector.status === "error" && "bg-red-400",
                  connector.status === "disconnected" && "bg-blue-400",
                )}
              />
              {connector.status === "connected"
                ? "Connected"
                : connector.status === "error"
                ? "Error"
                : "Disconnected"}
            </Badge>
          </div>
          <p className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50 mt-1">
            {connector.description}
          </p>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <div className="rounded-xl border border-[var(--color-border)] dark:border-white/10 p-4 bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]">
          <p className="text-xs text-[var(--color-text-tertiary)] dark:text-white/40 mb-1">Auth Type</p>
          <span className={cn("inline-block px-2 py-0.5 rounded text-xs font-medium", authInfo.color)}>
            {authInfo.label}
          </span>
        </div>

        <div className="rounded-xl border border-[var(--color-border)] dark:border-white/10 p-4 bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]">
          <p className="text-xs text-[var(--color-text-tertiary)] dark:text-white/40 mb-1">Category</p>
          <p className="text-sm font-medium text-[var(--color-text-primary)] dark:text-white capitalize">
            {connector.category}
          </p>
        </div>
      </div>

      {/* Connected State */}
      {isConnected && (
        <div className="space-y-6 mb-8">
          {/* Connection Info */}
          <div className="rounded-xl border border-[var(--color-border)] dark:border-white/10 p-5 bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] dark:text-white mb-4">
              Connection Details
            </h3>
            <dl className="space-y-3">
              <div className="flex justify-between">
                <dt className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50">Status</dt>
                <dd className="text-sm font-medium">
                  <span
                    className={cn(
                      connector.status === "connected"
                        ? "text-emerald-400"
                        : "text-red-400",
                    )}
                  >
                    {connector.status === "connected" ? "Active" : "Error"}
                  </span>
                </dd>
              </div>
              {connector.lastSyncAt && (
                <div className="flex justify-between">
                  <dt className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50">Last Sync</dt>
                  <dd className="text-sm text-[var(--color-text-primary)] dark:text-white">
                    {new Date(connector.lastSyncAt).toLocaleString()}
                  </dd>
                </div>
              )}
              {connector.errorMessage && (
                <div className="flex justify-between">
                  <dt className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50">Error</dt>
                  <dd className="text-sm text-red-400 max-w-[250px] text-right">
                    {connector.errorMessage}
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Actions */}
          <div className="flex flex-wrap gap-3">
            <button
              onClick={handleTest}
              disabled={testing}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20",
                testing && "opacity-50 cursor-not-allowed",
              )}
            >
              {testing ? "Testing..." : "Test Connection"}
            </button>

            {isOAuth && (
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className={cn(
                  "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                  "bg-blue-500/10 text-blue-600 dark:text-blue-400 hover:bg-blue-500/20",
                  refreshing && "opacity-50 cursor-not-allowed",
                )}
              >
                {refreshing ? "Refreshing..." : "Refresh Token"}
              </button>
            )}

            <button
              onClick={handleDisconnect}
              disabled={disconnecting}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all",
                "bg-red-500/10 text-red-600 dark:text-red-400 hover:bg-red-500/20",
                disconnecting && "opacity-50 cursor-not-allowed",
              )}
            >
              {disconnecting ? "Disconnecting..." : "Disconnect"}
            </button>
          </div>
        </div>
      )}

      {/* Disconnected State */}
      {!isConnected && (
        <div className="rounded-xl border border-[var(--color-border)] dark:border-white/10 p-6 bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)] mb-8">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] dark:text-white mb-2">
            Connect {connector.name}
          </h3>
          <p className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50 mb-4">
            {isOAuth
              ? `Authorize Anansi to access your ${connector.name} account.`
              : `Enter your ${connector.name} API key to connect.`}
          </p>
          <button
            onClick={() => setShowOAuth(true)}
            className="px-5 py-2.5 rounded-lg text-sm font-medium bg-[var(--color-bg-cta)] text-white hover:opacity-90 transition-opacity"
          >
            {isOAuth ? "Connect with OAuth" : "Enter API Key"}
          </button>
        </div>
      )}

      {/* Scopes Info (for OAuth) */}
      {isOAuth && (
        <div className="rounded-xl border border-[var(--color-border)] dark:border-white/10 p-5 bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] dark:text-white mb-3">
            Required Permissions
          </h3>
          <p className="text-xs text-[var(--color-text-tertiary)] dark:text-white/40 mb-3">
            Anansi requests the following OAuth scopes:
          </p>
          <ul className="space-y-1.5">
            {(connector as unknown as { scopes?: string[] }).scopes?.map((scope: string) => (
              <li key={scope} className="flex items-center gap-2 text-xs text-[var(--color-text-secondary)] dark:text-white/70">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-emerald-400 flex-shrink-0">
                  <path d="M9 12l2 2 4-4" />
                </svg>
                <code className="text-[10px] bg-white/5 px-1.5 py-0.5 rounded">{scope}</code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Error banner */}
      {error && (
        <div className="mt-6 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* OAuth Modal (for re-connecting) */}
      {showOAuth && (
        <OAuthModal
          connector={connector}
          onClose={() => setShowOAuth(false)}
          onSuccess={handleConnectSuccess}
        />
      )}
    </div>
  );
}
