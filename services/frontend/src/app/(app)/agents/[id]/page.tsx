/**
 * Agent Workshop Page — Full-screen agent editor with React Flow canvas.
 *
 * "/agents/[id]" — Main workspace for editing an agent visually.
 * Features: Block palette, infinite canvas, config panel, test panel,
 * undo/redo, zoom controls, auto-layout.
 */

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
  Panel,
  useReactFlow,
  ReactFlowProvider,
  type ReactFlowInstance,
  type Node,
  type Edge,
  MarkerType,
  SelectionMode,
} from "reactflow";
import "reactflow/dist/style.css";
import {
  Save,
  Play,
  Beaker,
  Share2,
  Upload,
  Undo2,
  Redo2,
  ZoomIn,
  ZoomOut,
  Maximize2,
  LayoutPanelTop,
  Layers,
  Clock,
  Bug,
  CheckCircle2,
  AlertTriangle,
  Edit3,
} from "lucide-react";
import { useWorkshopStore, type WorkshopNodeData } from "@/stores/workshop";
import { BlockPalette } from "@/components/workshop/BlockPalette";
import { BlockConfigPanel } from "@/components/workshop/BlockConfigPanel";
import { AgentTestPanel } from "@/components/workshop/AgentTestPanel";
import {
  TriggerNode,
  AiNode,
  ActionNode,
  LogicNode,
  ConnectorNode,
} from "@/components/workshop/CanvasNode";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { cn } from "@/lib/utils";

// ─── Node Types ─────────────────────────────────────────────────────────────────

const NODE_TYPES = {
  trigger: TriggerNode,
  ai: AiNode,
  action: ActionNode,
  logic: LogicNode,
  connector: ConnectorNode,
};

// ─── Default Edge Style ─────────────────────────────────────────────────────────

const DEFAULT_EDGE_OPTIONS = {
  type: "smoothstep",
  animated: true,
  style: { stroke: "#F59E0B", strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: "#F59E0B" },
};

// ─── Inner Workshop (needs ReactFlowProvider) ──────────────────────────────────

function WorkshopInner() {
  const params = useParams();
  const router = useRouter();
  const agentId = params?.id as string;
  const reactFlowInstance = useReactFlow();

  // Store
  const {
    nodes,
    edges,
    selectedNodeId,
    isDirty,
    agentName,
    agentVersion,
    isSaving,
    lastSavedAt,
    testMode,
    setAgentMeta,
    setNodes,
    setEdges,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    removeSelectedNode,
    undo,
    redo,
    canUndo,
    canRedo,
    saveAgent,
    loadAgent,
    setIsSaving,
  } = useWorkshopStore();

  // Local state
  const [testPanelOpen, setTestPanelOpen] = useState(false);
  const [showPalette, setShowPalette] = useState(true);
  const [showConfig, setShowConfig] = useState(true);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [agentNameEditing, setAgentNameEditing] = useState(false);
  const [agentNameValue, setAgentNameValue] = useState(agentName);
  const dropZoneRef = useRef<HTMLDivElement>(null);

  // Load agent on mount
  useEffect(() => {
    if (agentId && agentId !== "new" && agentId !== "canvas") {
      loadAgent(agentId).catch((err) => {
        console.error("Failed to load agent:", err);
      });
    }
  }, [agentId, loadAgent]);

  // Sync agent name
  useEffect(() => {
    setAgentNameValue(agentName);
  }, [agentName]);

  // ── Save handler ───────────────────────────────────────────────────────────

  const handleSave = useCallback(async () => {
    if (!isDirty) return;
    setSaveStatus("saving");
    try {
      await saveAgent();
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    } catch {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    }
  }, [saveAgent, isDirty]);

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ctrl+S / Cmd+S
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        e.preventDefault();
        handleSave();
      }
      // Ctrl+Z / Cmd+Z — undo
      if ((e.metaKey || e.ctrlKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      // Ctrl+Shift+Z / Cmd+Shift+Z — redo
      if ((e.metaKey || e.ctrlKey) && e.key === "z" && e.shiftKey) {
        e.preventDefault();
        redo();
      }
      // Delete / Backspace — remove selected
      if (e.key === "Delete" || e.key === "Backspace") {
        if (document.activeElement?.tagName !== "INPUT" &&
            document.activeElement?.tagName !== "TEXTAREA" &&
            document.activeElement?.getAttribute("contenteditable") !== "true") {
          removeSelectedNode();
        }
      }
      // Ctrl+T / Cmd+T — toggle test panel
      if ((e.metaKey || e.ctrlKey) && e.key === "t") {
        e.preventDefault();
        setTestPanelOpen((p) => !p);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleSave, undo, redo, removeSelectedNode]);

  // ── Drag and Drop ──────────────────────────────────────────────────────────

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    if (dropZoneRef.current) {
      dropZoneRef.current.style.outline = "2px dashed rgba(245, 158, 11, 0.5)";
    }
  }, []);

  const onDragLeave = useCallback(() => {
    if (dropZoneRef.current) {
      dropZoneRef.current.style.outline = "none";
    }
  }, []);

  const onDrop = useCallback(
    (event: React.DragEvent) => {
      event.preventDefault();
      if (dropZoneRef.current) {
        dropZoneRef.current.style.outline = "none";
      }

      const raw = event.dataTransfer.getData("application/reactflow") ||
                  event.dataTransfer.getData("text/plain");
      if (!raw) return;

      try {
        const data = JSON.parse(raw);
        const { type, subtype } = data;

        if (!type || !subtype) return;

        // Get canvas coordinates from mouse position
        const bounds = dropZoneRef.current?.getBoundingClientRect();
        if (!bounds) return;

        const position = reactFlowInstance.screenToFlowPosition({
          x: event.clientX - bounds.left,
          y: event.clientY - bounds.top,
        });

        addNode(type, subtype, position);
      } catch {
        // Ignore invalid drag data
      }
    },
    [reactFlowInstance, addNode]
  );

  // ── Auto-layout ───────────────────────────────────────────────────────────

  const handleAutoLayout = useCallback(() => {
    const currentNodes = reactFlowInstance.getNodes();
    if (currentNodes.length === 0) return;

    // Simple grid layout: top-to-bottom by connected groups
    const sorted = [...currentNodes].sort((a, b) => {
      const typeOrder = ["trigger", "ai", "logic", "action", "connector"];
      const aIdx = typeOrder.indexOf(a.type || "");
      const bIdx = typeOrder.indexOf(b.type || "");
      return aIdx - bIdx;
    });

    const layerMap: Record<string, number> = {};
    const edges = reactFlowInstance.getEdges();
    for (const node of sorted) {
      layerMap[node.id] = 0;
    }

    // Compute layers based on edges (source comes before target)
    let changed = true;
    while (changed) {
      changed = false;
      for (const edge of edges) {
        const srcLayer = layerMap[edge.source] ?? 0;
        const tgtLayer = layerMap[edge.target] ?? 0;
        if (tgtLayer <= srcLayer) {
          layerMap[edge.target] = srcLayer + 1;
          changed = true;
        }
      }
    }

    const SPACING_X = 300;
    const SPACING_Y = 150;
    const layerCounts: Record<number, number> = {};
    const layerPositions: Record<number, number> = {};

    for (const node of sorted) {
      const layer = layerMap[node.id] ?? 0;
      layerCounts[layer] = (layerCounts[layer] || 0) + 1;
    }

    let totalHeight = 0;
    for (const [layer, count] of Object.entries(layerCounts)) {
      layerPositions[Number(layer)] = totalHeight;
      totalHeight += count * 80 + SPACING_Y;
    }

    const updatedNodes = sorted.map((node) => {
      const layer = layerMap[node.id] ?? 0;
      const countInLayer = layerCounts[layer] || 1;
      const layerStart = layerPositions[layer] || 0;
      const idx = sorted.filter((n) => (layerMap[n.id] ?? 0) === layer).indexOf(node);
      const x = layer * SPACING_X + 100;
      const y = layerStart + idx * 80;
      return { ...node, position: { x, y } };
    });

    useWorkshopStore.getState().pushHistory();
    reactFlowInstance.setNodes(updatedNodes);
  }, [reactFlowInstance]);

  // ── Name change ───────────────────────────────────────────────────────────

  const handleNameSubmit = useCallback(() => {
    setAgentMeta({ name: agentNameValue });
    setAgentNameEditing(false);
  }, [agentNameValue, setAgentMeta]);

  // ── Zoom helpers ──────────────────────────────────────────────────────────

  const handleZoomIn = () => reactFlowInstance.zoomIn();
  const handleZoomOut = () => reactFlowInstance.zoomOut();
  const handleFitView = () => reactFlowInstance.fitView({ padding: 0.2 });

  // ── Format last saved ─────────────────────────────────────────────────────

  const formattedLastSaved = useMemo(() => {
    if (!lastSavedAt) return null;
    const d = new Date(lastSavedAt);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
  }, [lastSavedAt]);

  return (
    <div className="fixed inset-0 top-14 left-60 flex flex-col bg-[var(--color-bg-deepest)] z-10">
      {/* ═══ Top Bar ═══ */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] shrink-0">
        {/* Left: Agent name + save */}
        <div className="flex items-center gap-3 min-w-0">
          {agentNameEditing ? (
            <input
              type="text"
              value={agentNameValue}
              onChange={(e) => setAgentNameValue(e.target.value)}
              onBlur={handleNameSubmit}
              onKeyDown={(e) => e.key === "Enter" && handleNameSubmit()}
              className="px-2 py-1 rounded-md bg-[var(--color-surface-elevated)] border border-amber-500/40 text-sm font-heading font-bold text-[var(--color-text-primary)] focus:outline-none"
              autoFocus
            />
          ) : (
            <button
              onClick={() => setAgentNameEditing(true)}
              className="flex items-center gap-2 text-sm font-heading font-bold text-[var(--color-text-primary)] hover:text-amber-400 transition-colors"
            >
              {agentName}
              <Edit3 className="h-3 w-3 text-[var(--color-text-muted)]" />
            </button>
          )}

          {/* Save status */}
          {saveStatus === "saving" && (
            <span className="text-xs text-amber-400 animate-pulse">Saving...</span>
          )}
          {saveStatus === "saved" && (
            <span className="text-xs text-semantic-success flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Saved
            </span>
          )}
          {saveStatus === "error" && (
            <span className="text-xs text-semantic-error flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" /> Save failed
            </span>
          )}
          {isDirty && saveStatus === "idle" && (
            <span className="text-xs text-[var(--color-text-muted)]">Unsaved changes</span>
          )}
        </div>

        {/* Center */}
        <div className="flex items-center gap-1">
          <AnansiButton
            variant="ghost"
            size="sm"
            icon={<Save className="h-4 w-4" />}
            onClick={handleSave}
            disabled={!isDirty}
          >
            Save
          </AnansiButton>

          <AnansiButton
            variant="ghost"
            size="sm"
            icon={<Beaker className="h-4 w-4" />}
            onClick={() => setTestPanelOpen(true)}
          >
            Test
          </AnansiButton>

          <AnansiButton
            variant="primary"
            size="sm"
            icon={<Play className="h-4 w-4" />}
            onClick={() => setTestPanelOpen(true)}
          >
            Run
          </AnansiButton>

          <AnansiButton
            variant="ghost"
            size="sm"
            icon={<Share2 className="h-4 w-4" />}
          >
            Share
          </AnansiButton>

          <AnansiButton
            variant="secondary"
            size="sm"
            icon={<Upload className="h-4 w-4" />}
          >
            Publish
          </AnansiButton>
        </div>

        {/* Right: version */}
        <div className="text-xs text-[var(--color-text-muted)]">
          v{agentVersion}
        </div>
      </div>

      {/* ═══ Canvas Area ═══ */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Block Palette */}
        <div
          className={cn(
            "w-60 shrink-0 border-r border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] overflow-y-auto transition-all duration-200",
            !showPalette && "w-0 overflow-hidden"
          )}
        >
          <BlockPalette />
        </div>

        {/* Center: React Flow Canvas */}
        <div
          ref={dropZoneRef}
          className="flex-1 relative"
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={NODE_TYPES}
            defaultEdgeOptions={DEFAULT_EDGE_OPTIONS}
            fitView
            snapToGrid
            snapGrid={[20, 20]}
            minZoom={0.25}
            maxZoom={2}
            selectionMode={SelectionMode.Partial}
            deleteKeyCode={["Delete", "Backspace"]}
            multiSelectionKeyCode="Shift"
            panOnDrag
            zoomOnScroll
            selectNodesOnDrag
          >
            {/* Grid background */}
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="rgba(255,255,255,0.05)"
            />

            {/* Minimap */}
            <MiniMap
              nodeStrokeColor="#F59E0B"
              nodeColor="rgba(245,158,11,0.2)"
              nodeBorderRadius={4}
              maskColor="rgba(0,0,0,0.4)"
              style={{ backgroundColor: "rgba(28,25,23,0.8)" }}
            />

            {/* Controls */}
            <Controls
              showInteractive={false}
              className="!bg-[var(--color-surface-elevated)] !border-[var(--color-border-subtle)] !rounded-lg !shadow-glass-md"
            />

            {/* Top-left Toolbar */}
            <Panel position="top-left">
              <div className="flex gap-1">
                <button
                  onClick={undo}
                  disabled={!canUndo()}
                  className="p-1.5 rounded-md hover:bg-white/5 disabled:opacity-30 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                  title="Undo (Ctrl+Z)"
                >
                  <Undo2 className="h-4 w-4" />
                </button>
                <button
                  onClick={redo}
                  disabled={!canRedo()}
                  className="p-1.5 rounded-md hover:bg-white/5 disabled:opacity-30 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                  title="Redo (Ctrl+Shift+Z)"
                >
                  <Redo2 className="h-4 w-4" />
                </button>
                <div className="w-px bg-[var(--color-border-subtle)] mx-1" />
                <button
                  onClick={handleAutoLayout}
                  className="p-1.5 rounded-md hover:bg-white/5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                  title="Auto Layout"
                >
                  <LayoutPanelTop className="h-4 w-4" />
                </button>
              </div>
            </Panel>

            {/* Bottom-center info bar */}
            <Panel position="bottom-center">
              <div className="flex items-center gap-4 px-4 py-1.5 rounded-lg bg-[var(--color-bg-surface)]/80 backdrop-blur-xl border border-[var(--color-border-subtle)] text-[11px] text-[var(--color-text-muted)]">
                <span className="flex items-center gap-1">
                  <Layers className="h-3 w-3" /> {nodes.length} blocks
                </span>
                <span className="flex items-center gap-1">
                  v{agentVersion}
                </span>
                {formattedLastSaved && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" /> {formattedLastSaved}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Bug className="h-3 w-3" /> {testMode ? "Test" : "Live"}
                </span>
              </div>
            </Panel>
          </ReactFlow>
        </div>

        {/* Right: Config Panel */}
        <div
          className={cn(
            "w-72 shrink-0 border-l border-[var(--color-border-subtle)] bg-[var(--color-bg-surface)] overflow-y-auto transition-all duration-200",
            !showConfig && "w-0 overflow-hidden"
          )}
        >
          <BlockConfigPanel />
        </div>
      </div>

      {/* ═══ Test Panel (slide-out) ═══ */}
      <AgentTestPanel
        isOpen={testPanelOpen}
        onClose={() => setTestPanelOpen(false)}
      />
    </div>
  );
}

// ─── Wrapper (ReactFlowProvider required for hooks) ────────────────────────────

export default function AgentWorkshopPage() {
  return (
    <ReactFlowProvider>
      <WorkshopInner />
    </ReactFlowProvider>
  );
}
