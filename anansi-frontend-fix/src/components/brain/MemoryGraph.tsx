"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { cn } from "../../lib/utils";
import type { GraphNode, GraphEdge } from "../../stores/brain";

// ─── Types ──────────────────────────────────────────────────────────────────────

interface MemoryGraphProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onNodeClick?: (nodeId: string) => void;
  onNodeHover?: (nodeId: string | null) => void;
  onLinkCreate?: (sourceId: string, targetId: string) => void;
  selectedNodeId?: string | null;
  hoveredNodeId?: string | null;
  filters?: {
    tags?: string[];
    types?: string[];
  };
  width?: number;
  height?: number;
  className?: string;
  interactive?: boolean;
  showLabels?: boolean;
  minZoom?: number;
  maxZoom?: number;
}

interface SimulatedNode {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  title: string;
  type: string;
  tags: string[];
  linkCount: number;
  isSelected: boolean;
  isHovered: boolean;
}

interface SimulatedEdge {
  source: string;
  target: string;
  color: string;
  width: number;
  linkType: string;
}

// ─── Color mapping ──────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  fact: "#D6D3D1",
  preference: "#8B5CF6",
  pattern: "#F59E0B",
  relation: "#14B8A6",
  daily_note: "#3B82F6",
  agent_output: "#F97316",
  archived: "#78716C",
};

const LINK_COLORS: Record<string, string> = {
  related_to: "#44403C",
  categorized_as: "#8B5CF6",
  causes: "#F97316",
  contradicts: "#EF4444",
  mentioned_in: "#3B82F6",
  supports: "#22C55E",
  follows_from: "#14B8A6",
  user_defined: "#D97706",
};

// ─── Helper ─────────────────────────────────────────────────────────────────────

function getNodeColor(type: string, isSelected: boolean, isHovered: boolean): string {
  const base = TYPE_COLORS[type] || "#A8A29E";
  if (isSelected) return "#D97706";
  if (isHovered) return "#F59E0B";
  return base;
}

function getLinkColor(linkType: string): string {
  return LINK_COLORS[linkType] || "#44403C";
}

function getNodeRadius(linkCount: number): number {
  // Scale: min 6, max 20
  return Math.max(6, Math.min(20, 6 + linkCount * 2));
}

// ─── Simple force simulation (pure JS, no external deps) ────────────────────────

function runForceSimulation(
  simNodes: SimulatedNode[],
  simEdges: SimulatedEdge[],
  width: number,
  height: number,
  iterations: number = 100,
): SimulatedNode[] {
  const nodes = simNodes.map((n) => ({ ...n }));
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  const centerForce = 0.01;
  const repulsionForce = 500;
  const edgeLength = 120;
  const edgeForce = 0.05;
  const damping = 0.85;

  for (let iter = 0; iter < iterations; iter++) {
    // Center gravity
    for (const node of nodes) {
      node.vx += (width / 2 - node.x) * centerForce;
      node.vy += (height / 2 - node.y) * centerForce;
    }

    // Repulsion between all nodes
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i];
        const b = nodes[j];
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
        const force = repulsionForce / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }

    // Edge attraction
    for (const edge of simEdges) {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (!source || !target) continue;

      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
      const force = (dist - edgeLength) * edgeForce;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      source.vx += fx;
      source.vy += fy;
      target.vx -= fx;
      target.vy -= fy;
    }

    // Apply velocity with damping
    for (const node of nodes) {
      node.vx *= damping;
      node.vy *= damping;
      node.x += node.vx;
      node.y += node.vy;
    }
  }

  return nodes;
}

// ─── Component ───────────────────────────────────────────────────────────────────

export function MemoryGraph({
  nodes,
  edges,
  onNodeClick,
  onNodeHover,
  onLinkCreate,
  selectedNodeId,
  hoveredNodeId,
  filters,
  width = 800,
  height = 600,
  className,
  interactive = true,
  showLabels = true,
  minZoom = 0.3,
  maxZoom = 3,
}: MemoryGraphProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width, height });
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [dragNode, setDragNode] = useState<string | null>(null);
  const [linkSource, setLinkSource] = useState<string | null>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    node: SimulatedNode;
    x: number;
    y: number;
  } | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Filter nodes
  const filteredNodes = useMemo(() => {
    if (!filters?.tags?.length && !filters?.types?.length) return nodes;
    return nodes.filter((n) => {
      if (filters?.tags?.length && !filters.tags.some((t) => n.tags.includes(t))) return false;
      if (filters?.types?.length && !filters.types.includes(n.type)) return false;
      return true;
    });
  }, [nodes, filters]);

  const filteredNodeIds = useMemo(
    () => new Set(filteredNodes.map((n) => n.id)),
    [filteredNodes],
  );

  const filteredEdges = useMemo(
    () => edges.filter((e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target)),
    [edges, filteredNodeIds],
  );

  // Build simulated nodes
  const simNodes: SimulatedNode[] = useMemo(
    () =>
      filteredNodes.map((n) => ({
        id: n.id,
        x: Math.random() * dimensions.width,
        y: Math.random() * dimensions.height,
        vx: 0,
        vy: 0,
        radius: getNodeRadius(n.linksCount),
        color: getNodeColor(n.type, n.id === selectedNodeId, n.id === hoveredNodeId),
        title: n.title,
        type: n.type,
        tags: n.tags,
        linkCount: n.linksCount,
        isSelected: n.id === selectedNodeId,
        isHovered: n.id === hoveredNodeId,
      })),
    [filteredNodes, selectedNodeId, hoveredNodeId, dimensions],
  );

  const simEdges: SimulatedEdge[] = useMemo(
    () =>
      filteredEdges.map((e) => ({
        source: e.source,
        target: e.target,
        color: getLinkColor(e.linkType),
        width: Math.max(1, e.strength * 3),
        linkType: e.linkType,
      })),
    [filteredEdges],
  );

  // Run simulation once
  const simulatedNodes = useMemo(
    () => runForceSimulation(simNodes, simEdges, dimensions.width, dimensions.height, 150),
    [simNodes, simEdges, dimensions],
  );

  const nodeMap = useMemo(
    () => new Map(simulatedNodes.map((n) => [n.id, n])),
    [simulatedNodes],
  );

  // Resize observer
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setDimensions({
          width: entry.contentRect.width || width,
          height: entry.contentRect.height || height,
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  }, [width, height]);

  // Draw canvas
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = dimensions.width * dpr;
    canvas.height = dimensions.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear
    ctx.fillStyle = "transparent";
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    ctx.save();
    ctx.translate(pan.x, pan.y);
    ctx.scale(zoom, zoom);

    // Draw edges
    for (const edge of simEdges) {
      const source = nodeMap.get(edge.source);
      const target = nodeMap.get(edge.target);
      if (!source || !target) continue;

      ctx.beginPath();
      ctx.moveTo(source.x, source.y);
      ctx.lineTo(target.x, target.y);
      ctx.strokeStyle = edge.color + "60";
      ctx.lineWidth = edge.width;
      ctx.stroke();
    }

    // Draw nodes
    for (const node of simulatedNodes) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();

      if (node.isSelected) {
        ctx.strokeStyle = "#F59E0B";
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Label
      if (showLabels && zoom > 0.5) {
        ctx.fillStyle = "#D6D3D1";
        ctx.font = "11px Inter, system-ui, sans-serif";
        ctx.textAlign = "center";
        ctx.fillText(node.title, node.x, node.y + node.radius + 14);
      }
    }

    ctx.restore();

    animFrameRef.current = requestAnimationFrame(draw);
  }, [simulatedNodes, simEdges, nodeMap, dimensions, zoom, pan, showLabels]);

  useEffect(() => {
    animFrameRef.current = requestAnimationFrame(draw);
    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [draw]);

  // Find node at coordinates
  const findNodeAt = useCallback(
    (clientX: number, clientY: number): SimulatedNode | null => {
      const canvas = canvasRef.current;
      if (!canvas) return null;
      const rect = canvas.getBoundingClientRect();
      const x = (clientX - rect.left - pan.x) / zoom;
      const y = (clientY - rect.top - pan.y) / zoom;

      for (const node of simulatedNodes) {
        const dx = x - node.x;
        const dy = y - node.y;
        if (dx * dx + dy * dy <= node.radius * node.radius) {
          return node;
        }
      }
      return null;
    },
    [simulatedNodes, zoom, pan],
  );

  // Mouse handlers
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!interactive) return;
      const node = findNodeAt(e.clientX, e.clientY);
      if (node) {
        setDragNode(node.id);
      } else if (linkSource) {
        const target = findNodeAt(e.clientX, e.clientY);
        if (target && target.id !== linkSource) {
          onLinkCreate?.(linkSource, target.id);
        }
        setLinkSource(null);
      }
    },
    [interactive, findNodeAt, linkSource, onLinkCreate],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (dragNode) {
        const node = nodeMap.get(dragNode);
        if (node) {
          const canvas = canvasRef.current;
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          node.x = (e.clientX - rect.left - pan.x) / zoom;
          node.y = (e.clientY - rect.top - pan.y) / zoom;
        }
      } else {
        const node = findNodeAt(e.clientX, e.clientY);
        if (node) {
          onNodeHover?.(node.id);
          setTooltip({ node, x: e.clientX + 12, y: e.clientY - 10 });
        } else {
          onNodeHover?.(null);
          setTooltip(null);
        }
      }
    },
    [dragNode, findNodeAt, nodeMap, zoom, pan, onNodeHover],
  );

  const handleMouseUp = useCallback(() => {
    if (dragNode) {
      onNodeClick?.(dragNode);
      setDragNode(null);
    }
  }, [dragNode, onNodeClick]);

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      setZoom((z) => Math.max(minZoom, Math.min(maxZoom, z * delta)));
    },
    [minZoom, maxZoom],
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent) => {
      const node = findNodeAt(e.clientX, e.clientY);
      if (node) {
        // Toggle link source
        if (linkSource === node.id) {
          setLinkSource(null);
        } else {
          setLinkSource(node.id);
        }
      }
    },
    [findNodeAt, linkSource],
  );

  return (
    <div
      ref={containerRef}
      className={cn("relative overflow-hidden rounded-lg", className)}
      style={{ width: "100%", height: "100%", minHeight: height }}
    >
      <canvas
        ref={canvasRef}
        className="w-full h-full cursor-grab active:cursor-grabbing"
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onWheel={handleWheel}
        onDoubleClick={handleDoubleClick}
      />

      {/* Link source indicator */}
      {linkSource && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/30 text-amber-400 text-xs">
          Click a target node to create a link (or click again to cancel)
        </div>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div
          ref={tooltipRef}
          className="absolute z-50 px-3 py-2 rounded-lg glass-elevated text-xs pointer-events-none"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          <div className="font-semibold text-[var(--color-text-primary)]">
            {tooltip.node.title}
          </div>
          <div className="text-[var(--color-text-muted)] mt-0.5">
            {tooltip.node.type} · {tooltip.node.linkCount} links
          </div>
          {tooltip.node.tags.length > 0 && (
            <div className="flex gap-1 mt-1">
              {tooltip.node.tags.slice(0, 3).map((t) => (
                <span key={t} className="text-xs text-amber-500">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Zoom controls */}
      {interactive && (
        <div className="absolute bottom-3 right-3 flex flex-col gap-1">
          <button
            onClick={() => setZoom((z) => Math.min(maxZoom, z * 1.2))}
            className="w-8 h-8 rounded-lg glass-interactive flex items-center justify-center text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          >
            +
          </button>
          <button
            onClick={() => setZoom((z) => Math.max(minZoom, z * 0.8))}
            className="w-8 h-8 rounded-lg glass-interactive flex items-center justify-center text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
          >
            −
          </button>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-3 left-3 flex flex-wrap gap-3">
        {Object.entries(TYPE_COLORS).slice(0, 4).map(([type, color]) => (
          <div key={type} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[10px] text-[var(--color-text-muted)] capitalize">{type}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
