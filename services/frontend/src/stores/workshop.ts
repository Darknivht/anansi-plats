/**
 * Workshop Store — Zustand state management for the agent builder canvas.
 *
 * Manages React Flow nodes/edges, undo/redo history, serialization,
 * and connections to the agent service API.
 */

"use client";

import { create } from "zustand";
import type {
  AgentBlock,
  AgentEdge,
  AgentDefinition,
  Node,
  Edge,
  Viewport,
  OnNodesChange,
  OnEdgesChange,
  Connection,
  XYPosition,
} from "reactflow";
import {
  applyNodeChanges,
  applyEdgeChanges,
  addEdge,
  MarkerType,
} from "reactflow";

// ── Types ──────────────────────────────────────────────────────────────────────

export interface WorkshopNodeData {
  type: string; // block type category
  subtype: string; // specific block subtype
  label: string;
  config: Record<string, unknown>;
  status: "idle" | "running" | "success" | "error";
  errorMessage?: string;
  configPreview?: string;
  icon?: string;
  color?: string;
}

export type WorkshopNode = Node<WorkshopNodeData>;
export type WorkshopEdge = Edge;

export interface HistoryEntry {
  nodes: WorkshopNode[];
  edges: WorkshopEdge[];
}

interface WorkshopState {
  // Canvas state
  nodes: WorkshopNode[];
  edges: WorkshopEdge[];
  selectedNodeId: string | null;
  viewport: Viewport;
  isDirty: boolean;
  testMode: boolean;

  // Undo/redo
  history: HistoryEntry[];
  historyIndex: number;
  maxHistory: number;

  // Agent metadata
  agentId: string | null;
  agentName: string;
  agentDescription: string;
  agentVersion: number;

  // Loading/saving
  isSaving: boolean;
  lastSavedAt: string | null;

  // Actions
  setNodes: (nodes: WorkshopNode[]) => void;
  setEdges: (edges: WorkshopEdge[]) => void;
  onNodesChange: OnNodesChange<WorkshopNode>;
  onEdgesChange: OnEdgesChange<WorkshopEdge>;
  onConnect: (connection: Connection) => void;
  addNode: (type: string, subtype: string, position?: XYPosition, config?: Record<string, unknown>) => string;
  updateNodeConfig: (nodeId: string, config: Record<string, unknown>) => void;
  removeNode: (nodeId: string) => void;
  removeSelectedNode: () => void;
  selectNode: (nodeId: string | null) => void;
  setViewport: (viewport: Viewport) => void;
  setAgentMeta: (data: { id?: string; name?: string; description?: string; version?: number }) => void;
  setTestMode: (enabled: boolean) => void;

  // Undo/redo
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // Serialization
  toAgentDefinition: () => AgentDefinition;
  fromAgentDefinition: (def: AgentDefinition, blockMeta?: Record<string, { label: string; icon?: string; color?: string }>) => void;

  // Persistence
  saveAgent: () => Promise<void>;
  loadAgent: (agentId: string) => Promise<void>;
  setIsSaving: (saving: boolean) => void;
  setLastSaved: (timestamp: string) => void;
  markClean: () => void;
}

const DEFAULT_VIEWPORT: Viewport = { x: 0, y: 0, zoom: 1 };

// ─── Helpers ───────────────────────────────────────────────────────────────────

let nodeCounter = 0;

function generateNodeId(): string {
  nodeCounter += 1;
  return `block_${Date.now()}_${nodeCounter}`;
}

function generateEdgeId(): string {
  return `edge_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

const BLOCK_LABELS: Record<string, string> = {
  "trigger.schedule": "Schedule",
  "trigger.webhook": "Webhook",
  "trigger.email_received": "Email Received",
  "trigger.message_received": "Message Received",
  "trigger.file_changed": "File Changed",
  "trigger.form_submitted": "Form Submitted",
  "trigger.event": "Platform Event",
  "ai.conversation": "AI Conversation",
  "ai.extract": "AI Extract",
  "ai.classify": "AI Classify",
  "ai.summarize": "AI Summarize",
  "ai.generate": "AI Generate",
  "ai.transform": "AI Transform",
  "action.send_email": "Send Email",
  "action.send_whatsapp": "Send WhatsApp",
  "action.create_crm_record": "Create CRM Record",
  "action.update_sheet": "Update Sheet",
  "action.http_request": "HTTP Request",
  "action.create_file": "Create File",
  "action.post_slack": "Post to Slack",
  "logic.condition": "Condition",
  "logic.filter": "Filter",
  "logic.router": "Router",
  "logic.delay": "Delay",
  "logic.loop": "Loop",
  "logic.wait": "Wait For",
};

const BLOCK_DEFAULTS: Record<string, Record<string, unknown>> = {
  "trigger.schedule": { cron: "0 9 * * *", timezone: "UTC" },
  "trigger.webhook": { method: "POST" },
  "trigger.email_received": { folder: "INBOX" },
  "trigger.message_received": { channel: "any" },
  "trigger.file_changed": { event: "any", recursive: false },
  "trigger.form_submitted": { fields: [], require_all_fields: false },
  "trigger.event": { event_type: "agent.completed", filter: {} },
  "ai.conversation": { system_prompt: "You are a helpful assistant.", model: "claude-sonnet-4" },
  "ai.extract": { prompt: "Extract key information.", model: "claude-haiku-3" },
  "ai.classify": { categories: [], model: "claude-haiku-3" },
  "ai.summarize": { length: "medium", style: "concise", model: "claude-haiku-3" },
  "ai.generate": { prompt: "Generate content.", format: "text", model: "claude-sonnet-4" },
  "ai.transform": { transformation: "Translate to English", model: "claude-haiku-3" },
  "action.send_email": { draft_only: false },
  "action.send_whatsapp": {},
  "action.create_crm_record": { fields: {} },
  "action.update_sheet": { mode: "append" },
  "action.http_request": { method: "GET", timeout_seconds: 30 },
  "action.create_file": {},
  "action.post_slack": { as_bot: true },
  "logic.condition": { expression: "data.score > 50", label_true: "True", label_false: "False" },
  "logic.filter": { condition: "True" },
  "logic.router": { cases: [], default_case: "Other" },
  "logic.delay": { duration: 5, unit: "seconds" },
  "logic.loop": { iterations: 10, batch_size: 1 },
  "logic.wait": { check_interval_seconds: 10, timeout_minutes: 60 },
};

const BLOCK_COLORS: Record<string, string> = {
  trigger: "#22C55E",
  ai: "#8B5CF6",
  action: "#F59E0B",
  logic: "#14B8A6",
  connector: "#3B82F6",
};

// ─── Store ──────────────────────────────────────────────────────────────────────

export const useWorkshopStore = create<WorkshopState>((set, get) => ({
  // Initial state
  nodes: [],
  edges: [],
  selectedNodeId: null,
  viewport: DEFAULT_VIEWPORT,
  isDirty: false,
  testMode: false,
  history: [],
  historyIndex: -1,
  maxHistory: 50,
  agentId: null,
  agentName: "Untitled Agent",
  agentDescription: "",
  agentVersion: 1,
  isSaving: false,
  lastSavedAt: null,

  // ── Node Operations ────────────────────────────────────────────────────────

  setNodes: (nodes) => {
    set({ nodes, isDirty: true });
  },

  setEdges: (edges) => {
    set({ edges, isDirty: true });
  },

  onNodesChange: (changes) => {
    set((state) => ({
      nodes: applyNodeChanges(changes, state.nodes) as WorkshopNode[],
      isDirty: true,
    }));
  },

  onEdgesChange: (changes) => {
    set((state) => {
      const newEdges = applyEdgeChanges(changes, state.edges) as WorkshopEdge[];
      return { edges: newEdges, isDirty: true };
    });
  },

  onConnect: (connection) => {
    set((state) => {
      const newEdge: WorkshopEdge = {
        ...connection,
        id: generateEdgeId(),
        type: "smoothstep",
        animated: true,
        style: { stroke: "#F59E0B", strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: "#F59E0B" },
      };
      const edges = addEdge(newEdge, state.edges) as WorkshopEdge[];
      get().pushHistory();
      return { edges, isDirty: true };
    });
  },

  addNode: (type, subtype, position, config) => {
    const blockKey = `${type}.${subtype}`;
    const id = generateNodeId();
    const label = BLOCK_LABELS[blockKey] || `${type}:${subtype}`;
    const defaults = BLOCK_DEFAULTS[blockKey] || {};

    const newNode: WorkshopNode = {
      id,
      type, // React Flow node type matches block type
      position: position || { x: 250 + Math.random() * 200, y: 150 + Math.random() * 200 },
      data: {
        type,
        subtype,
        label,
        config: { ...defaults, ...(config || {}) },
        status: "idle",
        color: BLOCK_COLORS[type] || "#A8A29E",
      },
    };

    get().pushHistory();
    set((state) => ({
      nodes: [...state.nodes, newNode],
      isDirty: true,
    }));

    return id;
  },

  updateNodeConfig: (nodeId, config) => {
    set((state) => {
      const nodes = state.nodes.map((n) => {
        if (n.id === nodeId) {
          return {
            ...n,
            data: { ...n.data, config: { ...n.data.config, ...config } },
          } as WorkshopNode;
        }
        return n;
      });
      return { nodes, isDirty: true };
    });
  },

  removeNode: (nodeId) => {
    get().pushHistory();
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
      isDirty: true,
    }));
  },

  removeSelectedNode: () => {
    const { selectedNodeId } = get();
    if (selectedNodeId) {
      get().removeNode(selectedNodeId);
    }
  },

  selectNode: (nodeId) => {
    set({ selectedNodeId: nodeId });
  },

  setViewport: (viewport) => {
    set({ viewport });
  },

  setAgentMeta: (data) => {
    set((state) => ({
      agentId: data.id !== undefined ? data.id : state.agentId,
      agentName: data.name !== undefined ? data.name : state.agentName,
      agentDescription: data.description !== undefined ? data.description : state.agentDescription,
      agentVersion: data.version !== undefined ? data.version : state.agentVersion,
    }));
  },

  setTestMode: (enabled) => {
    set({ testMode: enabled });
  },

  // ── Undo/Redo ──────────────────────────────────────────────────────────────

  pushHistory: () => {
    set((state) => {
      const entry: HistoryEntry = {
        nodes: JSON.parse(JSON.stringify(state.nodes)),
        edges: JSON.parse(JSON.stringify(state.edges)),
      };
      const newHistory = state.history.slice(0, state.historyIndex + 1);
      newHistory.push(entry);

      if (newHistory.length > state.maxHistory) {
        newHistory.shift();
      }

      return {
        history: newHistory,
        historyIndex: newHistory.length - 1,
      };
    });
  },

  undo: () => {
    set((state) => {
      if (state.historyIndex <= 0) return state;
      const newIndex = state.historyIndex - 1;
      const entry = state.history[newIndex];
      if (!entry) return state;
      return {
        nodes: JSON.parse(JSON.stringify(entry.nodes)),
        edges: JSON.parse(JSON.stringify(entry.edges)),
        historyIndex: newIndex,
        isDirty: true,
      };
    });
  },

  redo: () => {
    set((state) => {
      if (state.historyIndex >= state.history.length - 1) return state;
      const newIndex = state.historyIndex + 1;
      const entry = state.history[newIndex];
      if (!entry) return state;
      return {
        nodes: JSON.parse(JSON.stringify(entry.nodes)),
        edges: JSON.parse(JSON.stringify(entry.edges)),
        historyIndex: newIndex,
        isDirty: true,
      };
    });
  },

  canUndo: () => get().historyIndex > 0,
  canRedo: () => get().historyIndex < get().history.length - 1,

  // ── Serialization ──────────────────────────────────────────────────────────

  toAgentDefinition: () => {
    const { nodes, edges } = get();
    return {
      blocks: nodes.map((n) => ({
        id: n.id,
        type: n.data.type as AgentBlock["type"],
        subtype: n.data.subtype,
        config: n.data.config,
        position: { x: n.position.x, y: n.position.y },
      })),
      edges: edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || undefined,
      })),
      triggers: nodes
        .filter((n) => n.data.type === "trigger")
        .map((n) => ({
          type: n.data.subtype as "schedule" | "webhook" | "event",
          config: n.data.config as Record<string, unknown>,
        })),
    };
  },

  fromAgentDefinition: (def, blockMeta) => {
    const nodes: WorkshopNode[] = (def.blocks || []).map((b) => {
      const blockKey = `${b.type}.${b.subtype}`;
      const meta = blockMeta?.[b.id];
      const defaults = BLOCK_DEFAULTS[blockKey] || {};
      return {
        id: b.id,
        type: b.type,
        position: b.position || { x: 250, y: 150 },
        data: {
          type: b.type,
          subtype: b.subtype,
          label: meta?.label || BLOCK_LABELS[blockKey] || `${b.type}:${b.subtype}`,
          config: { ...defaults, ...b.config },
          status: "idle",
          color: BLOCK_COLORS[b.type] || "#A8A29E",
          icon: meta?.icon,
        },
      };
    });

    const edges: WorkshopEdge[] = (def.edges || []).map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      label: e.label,
      type: "smoothstep",
      animated: true,
      style: { stroke: "#F59E0B", strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: "#F59E0B" },
    }));

    const historyEntry: HistoryEntry = {
      nodes: JSON.parse(JSON.stringify(nodes)),
      edges: JSON.parse(JSON.stringify(edges)),
    };

    set({
      nodes,
      edges,
      history: [historyEntry],
      historyIndex: 0,
      isDirty: false,
      viewport: DEFAULT_VIEWPORT,
      selectedNodeId: null,
    });
  },

  // ── Persistence ────────────────────────────────────────────────────────────

  setIsSaving: (saving) => set({ isSaving: saving }),

  setLastSaved: (timestamp) => set({ lastSavedAt: timestamp }),

  markClean: () => set({ isDirty: false }),

  saveAgent: async () => {
    const { agentId, agentName, agentDescription, toAgentDefinition, setIsSaving, setLastSaved, isDirty } = get();
    if (!isDirty) return;

    setIsSaving(true);
    try {
      const definition = toAgentDefinition();
      const { api } = await import("@/lib/api");

      if (agentId) {
        // Update existing agent
        await api.patch(`/api/v1/agents/${agentId}`, {
          name: agentName,
          description: agentDescription,
          definition,
        });
      } else {
        // Create new agent
        const result = await api.post<{ id: string }>("/api/v1/agents", {
          name: agentName,
          description: agentDescription,
          definition,
        });
        set({ agentId: result.id });
      }

      const now = new Date().toISOString();
      setLastSaved(now);
      get().markClean();
    } catch (err) {
      console.error("Failed to save agent:", err);
      throw err;
    } finally {
      setIsSaving(false);
    }
  },

  loadAgent: async (agentId) => {
    try {
      const { api } = await import("@/lib/api");
      const agent = await api.get<{
        id: string;
        name: string;
        description: string | null;
        definition: AgentDefinition;
        version: number;
      }>(`/api/v1/agents/${agentId}`);

      set({
        agentId: agent.id,
        agentName: agent.name,
        agentDescription: agent.description || "",
        agentVersion: agent.version,
      });

      get().fromAgentDefinition(agent.definition);
      get().markClean();
    } catch (err) {
      console.error("Failed to load agent:", err);
      throw err;
    }
  },
}));
