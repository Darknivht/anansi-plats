/**
 * Integrations Store — Zustand state management for connector connections.
 *
 * Manages:
 * - List of available connectors with status
 * - Active integration details
 * - Webhook registrations
 * - Connection state (connecting, connected, error)
 */

import { create } from "zustand";
import { api } from "../lib/api";
import type { Integration, Connector } from "../types";

// ─── Types ─────────────────────────────────────────────────────────────────

export type ConnectionStatus = "connected" | "disconnected" | "error" | "pending";

export interface ConnectorWithStatus extends Connector {
  status: ConnectionStatus;
  integrationId?: string;
  lastSyncAt?: string | null;
  errorMessage?: string | null;
  scopes?: string[];
}

export interface IntegrationStatusSummary {
  total: number;
  connected: number;
  error: number;
  available: number;
}

interface ConnectionsStatus {
  summary: IntegrationStatusSummary;
  connections: Array<{
    integrationId: string;
    connectorType: string;
    name: string;
    iconUrl: string;
    category: string;
    status: string;
    errorMessage: string | null;
    lastSyncAt: string | null;
  }>;
}

interface WebhookRegistration {
  webhookId: string;
  webhookUrl: string;
  secret: string;
  description: string;
  events: string[];
  active: boolean;
}

interface IntegrationState {
  // ── State ──
  connectors: ConnectorWithStatus[];
  selectedIntegration: Integration | null;
  statusSummary: IntegrationStatusSummary | null;
  isConnecting: boolean;
  isConnected: boolean;
  error: string | null;
  webhooks: WebhookRegistration[];

  // ── Actions ──
  fetchConnectors: () => Promise<void>;
  fetchIntegrationDetail: (id: string) => Promise<Integration | null>;
  initiateOAuth: (connectorKey: string, redirectUri: string) => Promise<{ authUrl: string; state: string } | null>;
  handleOAuthCallback: (connectorKey: string, code: string, state: string) => Promise<boolean>;
  connectApiKey: (connectorKey: string, apiKey: string, config?: Record<string, unknown>) => Promise<boolean>;
  disconnect: (integrationId: string) => Promise<boolean>;
  testConnection: (integrationId: string) => Promise<{ success: boolean; error?: string }>;
  fetchStatus: () => Promise<void>;
  refreshToken: (integrationId: string) => Promise<boolean>;
  registerWebhook: (agentId: string, config: Record<string, unknown>) => Promise<WebhookRegistration | null>;
  unregisterWebhook: (webhookId: string) => Promise<boolean>;
  fetchWebhooks: (agentId?: string) => Promise<void>;
  reset: () => void;
}

// ─── Store ─────────────────────────────────────────────────────────────────

const API_PREFIX = "/api/v1/integrations";

export const useIntegrationStore = create<IntegrationState>((set, get) => ({
  // ── Initial State ──
  connectors: [],
  selectedIntegration: null,
  statusSummary: null,
  isConnecting: false,
  isConnected: false,
  error: null,
  webhooks: [],

  // ── Fetch all connectors with status ──
  fetchConnectors: async () => {
    try {
      set({ error: null, isConnecting: true });
      const data = await api.get<
        Array<{
          key: string;
          name: string;
          description: string | null;
          icon_url: string | null;
          category: string;
          auth_type: string;
          is_connected: boolean;
          status: string;
          integration_id: string | null;
          last_sync_at: string | null;
          error_message: string | null;
        }>
      >(API_PREFIX);

      const connectors: ConnectorWithStatus[] = data.map((c) => ({
        id: c.key,
        key: c.key,
        name: c.name,
        description: c.description ?? null,
        iconUrl: c.icon_url ?? null,
        authType: c.auth_type as "oauth2" | "apikey" | "basic",
        isBuiltin: true,
        status: c.is_connected ? (c.status === "error" ? "error" : "connected") : "disconnected",
        integrationId: c.integration_id ?? undefined,
        lastSyncAt: c.last_sync_at,
        errorMessage: c.error_message,
      }));

      set({ connectors, isConnecting: false });
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to fetch connectors",
        isConnecting: false,
      });
    }
  },

  // ── Fetch single integration detail ──
  fetchIntegrationDetail: async (id: string) => {
    try {
      const data = await api.get<Integration>(`${API_PREFIX}/${id}`);
      set({ selectedIntegration: data });
      return data;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to fetch integration" });
      return null;
    }
  },

  // ── Initiate OAuth flow ──
  initiateOAuth: async (connectorKey: string, redirectUri: string) => {
    try {
      set({ error: null, isConnecting: true });
      const data = await api.post<{ auth_url: string; state: string; integration_id: string }>(
        `${API_PREFIX}/auth`,
        { connector_key: connectorKey, redirect_uri: redirectUri }
      );
      set({ isConnecting: false });
      return { authUrl: data.auth_url, state: data.state };
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to initiate OAuth",
        isConnecting: false,
      });
      return null;
    }
  },

  // ── Handle OAuth callback ──
  handleOAuthCallback: async (connectorKey: string, code: string, state: string) => {
    try {
      set({ error: null, isConnecting: true });
      await api.post(`${API_PREFIX}/auth/callback`, {
        connector_key: connectorKey,
        code,
        state,
      });
      set({ isConnecting: false, isConnected: true });
      await get().fetchConnectors();
      return true;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "OAuth callback failed",
        isConnecting: false,
      });
      return false;
    }
  },

  // ── Connect via API key ──
  connectApiKey: async (connectorKey: string, apiKey: string, config?: Record<string, unknown>) => {
    try {
      set({ error: null, isConnecting: true });
      await api.post(`${API_PREFIX}/connect`, {
        connector_key: connectorKey,
        api_key: apiKey,
        config: config ?? {},
      });
      set({ isConnecting: false, isConnected: true });
      await get().fetchConnectors();
      return true;
    } catch (err) {
      set({
        error: err instanceof Error ? err.message : "Failed to connect",
        isConnecting: false,
      });
      return false;
    }
  },

  // ── Disconnect ──
  disconnect: async (integrationId: string) => {
    try {
      set({ error: null });
      await api.post(`${API_PREFIX}/${integrationId}/disconnect`);
      set({ isConnected: false, selectedIntegration: null });
      await get().fetchConnectors();
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to disconnect" });
      return false;
    }
  },

  // ── Test connection ──
  testConnection: async (integrationId: string) => {
    try {
      set({ error: null });
      const result = await api.post<{ success: boolean; error?: string }>(
        `${API_PREFIX}/${integrationId}/test`
      );
      await get().fetchConnectors();
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Connection test failed";
      set({ error: msg });
      return { success: false, error: msg };
    }
  },

  // ── Fetch status ──
  fetchStatus: async () => {
    try {
      const data = await api.get<ConnectionsStatus>(`${API_PREFIX}/status`);
      set({ statusSummary: data.summary });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to fetch status" });
    }
  },

  // ── Refresh token ──
  refreshToken: async (integrationId: string) => {
    try {
      set({ error: null });
      await api.post(`${API_PREFIX}/${integrationId}/refresh`);
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Token refresh failed" });
      return false;
    }
  },

  // ── Webhooks ──
  registerWebhook: async (agentId: string, config: Record<string, unknown>) => {
    try {
      set({ error: null });
      const data = await api.post<WebhookRegistration>(
        `${API_PREFIX}/webhooks/register`,
        { agent_id: agentId, config }
      );
      await get().fetchWebhooks();
      return data;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to register webhook" });
      return null;
    }
  },

  unregisterWebhook: async (webhookId: string) => {
    try {
      set({ error: null });
      await api.post(`${API_PREFIX}/webhooks/${webhookId}/unregister`);
      await get().fetchWebhooks();
      return true;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to unregister webhook" });
      return false;
    }
  },

  fetchWebhooks: async (agentId?: string) => {
    try {
      const params = agentId ? { agent_id: agentId } : undefined;
      const data = await api.get<WebhookRegistration[]>(
        `${API_PREFIX}/webhooks`,
        { params }
      );
      set({ webhooks: data });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to fetch webhooks" });
    }
  },

  // ── Reset ──
  reset: () => {
    set({
      connectors: [],
      selectedIntegration: null,
      statusSummary: null,
      isConnecting: false,
      isConnected: false,
      error: null,
      webhooks: [],
    });
  },
}));
