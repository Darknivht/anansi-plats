"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import { useBrainStore } from "@/stores/brain";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { BrainIcon } from "@/components/ui/BrainIcon";
import { MemoryDetail } from "@/components/brain/MemoryDetail";
import { api } from "@/lib/api";
import type { MemoryNode } from "@/types";
import {
  Search,
  Plus,
  Grid3X3,
  List,
  Tag,
  Layers,
  Link2,
  Calendar,
  MoreHorizontal,
  Check,
  X,
  Brain,
  ChevronDown,
  ChevronUp,
  Download,
  Trash2,
  ExternalLink,
} from "lucide-react";

export default function BrainNodesPage() {
  const { searchNodes, searchResults, isSearching, loadStats } = useBrainStore();
  const [nodes, setNodes] = useState<MemoryNode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"list" | "grid">("list");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);

  // Load nodes
  useEffect(() => {
    loadNodes();
  }, []);

  const loadNodes = async () => {
    setIsLoading(true);
    try {
      const resp = await api.get<{ nodes: MemoryNode[] }>("/api/v1/brain/nodes", {
        params: { limit: 100 },
      });
      setNodes(resp.nodes);
    } catch (err) {
      console.error("Failed to load nodes:", err);
    }
    setIsLoading(false);
  };

  // Extract all unique tags
  const allTags = useMemo(() => {
    const tagSet = new Set<string>();
    nodes.forEach((n) => (n.tags || []).forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [nodes]);

  // Filter nodes
  const filteredNodes = useMemo(() => {
    let result = nodes;

    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (n) =>
          n.title.toLowerCase().includes(q) ||
          n.content.toLowerCase().includes(q),
      );
    }

    if (selectedTags.length > 0) {
      result = result.filter((n) =>
        selectedTags.some((t) => (n.tags || []).includes(t)),
      );
    }

    if (selectedTypes.length > 0) {
      result = result.filter((n) => selectedTypes.includes(n.type));
    }

    return result;
  }, [nodes, searchQuery, selectedTags, selectedTypes]);

  // Toggle tag selection
  const toggleTag = (tag: string) => {
    setSelectedTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag],
    );
  };

  const toggleType = (type: string) => {
    setSelectedTypes((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    );
  };

  // Expand/collapse
  const toggleExpand = (id: string) => {
    setExpandedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Selection
  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Delete selected
  const handleBatchDelete = async () => {
    for (const id of selectedIds) {
      try {
        await api.delete(`/api/v1/brain/nodes/${id}`);
      } catch (err) {
        console.error("Failed to delete:", id, err);
      }
    }
    setSelectedIds(new Set());
    loadNodes();
    loadStats();
  };

  // Format date
  const formatDate = (dateStr: string | undefined | null): string => {
    if (!dateStr) return "—";
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <Brain className="h-6 w-6 text-brand-amber-light" />
            Memory Library
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            {filteredNodes.length} nodes · Browse, search, and manage your knowledge
          </p>
        </div>
        <div className="flex items-center gap-2">
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => setViewMode(viewMode === "list" ? "grid" : "list")}
          >
            {viewMode === "list" ? <Grid3X3 className="h-4 w-4" /> : <List className="h-4 w-4" />}
          </AnansiButton>
          <AnansiButton variant="primary" size="sm" onClick={() => setShowCreateModal(true)}>
            <Plus className="h-4 w-4" />
            New Node
          </AnansiButton>
          {selectedIds.size > 0 && (
            <AnansiButton variant="danger" size="sm" onClick={handleBatchDelete}>
              <Trash2 className="h-4 w-4" />
              Delete ({selectedIds.size})
            </AnansiButton>
          )}
        </div>
      </div>

      {/* Search & filters */}
      <div className="flex flex-wrap gap-4">
        <div className="flex-1 min-w-[200px]">
          <Input
            placeholder="Search nodes..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            icon={<Search className="h-4 w-4" />}
          />
        </div>
        <div className="flex flex-wrap gap-1.5 items-center">
          {allTags.slice(0, 10).map((tag) => (
            <button
              key={tag}
              onClick={() => toggleTag(tag)}
              className={`text-xs px-2 py-1 rounded-full transition-colors ${
                selectedTags.includes(tag)
                  ? "bg-brand-amber/20 text-brand-amber-light border border-brand-amber/30"
                  : "bg-white/5 text-[var(--color-text-muted)] border border-transparent hover:border-[var(--color-border-subtle)]"
              }`}
            >
              {tag.replace("#", "")}
            </button>
          ))}
          {allTags.length > 10 && (
            <span className="text-xs text-[var(--color-text-muted)]">+{allTags.length - 10} more</span>
          )}
        </div>
      </div>

      {/* Node list */}
      {isLoading ? (
        <div className="space-y-3 animate-pulse">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-16 rounded-lg bg-white/5" />
          ))}
        </div>
      ) : filteredNodes.length === 0 ? (
        <GlassCard variant="base" padding="lg" className="text-center py-12">
          <Brain className="h-12 w-12 text-[var(--color-text-muted)] mx-auto mb-3" />
          <p className="text-[var(--color-text-muted)] mb-2">No nodes found</p>
          <p className="text-sm text-[var(--color-text-muted)] mb-4">
            {searchQuery ? "Try a different search term" : "Create your first memory node to get started"}
          </p>
          {!searchQuery && (
            <AnansiButton variant="primary" onClick={() => setShowCreateModal(true)}>
              <Plus className="h-4 w-4" />
              Create Node
            </AnansiButton>
          )}
        </GlassCard>
      ) : viewMode === "list" ? (
        <div className="space-y-2">
          {filteredNodes.map((node) => {
            const isExpanded = expandedNodes.has(node.id);
            const isSelected = selectedIds.has(node.id);
            const layers = node.layers || {};
            const hasLayers = !!(layers.l1Summary || layers.l2Highlights || layers.l4Compressed);

            return (
              <GlassCard
                key={node.id}
                variant={isSelected ? "elevated" : "base"}
                glow={isSelected ? "amber" : "none"}
                padding="sm"
                className="cursor-pointer"
              >
                <div className="flex items-center gap-3">
                  {/* Checkbox */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleSelect(node.id);
                    }}
                    className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                      isSelected
                        ? "bg-brand-amber border-brand-amber"
                        : "border-[var(--color-border-subtle)] hover:border-brand-amber/50"
                    }`}
                  >
                    {isSelected && <Check className="h-3 w-3 text-white" />}
                  </button>

                  {/* Expand */}
                  <button
                    onClick={() => toggleExpand(node.id)}
                    className="p-0.5 rounded hover:bg-white/10 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronUp className="h-3.5 w-3.5 text-[var(--color-text-muted)]" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5 text-[var(--color-text-muted)]" />
                    )}
                  </button>

                  {/* Content */}
                  <div
                    className="flex-1 min-w-0"
                    onClick={() => {
                      setSelectedNode(node);
                      setShowDetail(true);
                    }}
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                        {node.title}
                      </span>
                      <Badge variant="brand" size="sm" pill>
                        {node.type.replace(/_/g, " ")}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <div className="flex flex-wrap gap-1">
                        {(node.tags || []).slice(0, 3).map((t) => (
                          <span key={t} className="text-[10px] text-brand-amber-light">
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="flex items-center gap-3 text-xs text-[var(--color-text-muted)] shrink-0">
                    {hasLayers && <Layers className="h-3.5 w-3.5 text-brand-violet-light" />}
                    <div className="flex items-center gap-1">
                      <Link2 className="h-3 w-3" />
                      {node.links?.length ?? node.linksCount ?? 0}
                    </div>
                    <Calendar className="h-3 w-3" />
                    {formatDate(node.createdAt)}
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                    <p className="text-sm text-[var(--color-text-secondary)] line-clamp-3 whitespace-pre-wrap">
                      {node.content}
                    </p>
                    {layers.l1Summary && (
                      <p className="text-xs text-[var(--color-text-muted)] mt-2 italic">
                        Summary: {layers.l1Summary}
                      </p>
                    )}
                  </div>
                )}
              </GlassCard>
            );
          })}
        </div>
      ) : (
        /* Grid view */
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredNodes.map((node) => {
            const layers = node.layers || {};
            return (
              <GlassCard
                key={node.id}
                variant="interactive"
                padding="md"
                onClick={() => {
                  setSelectedNode(node);
                  setShowDetail(true);
                }}
              >
                <div className="flex items-start justify-between mb-2">
                  <Badge variant="brand" size="sm" pill>
                    {node.type.replace(/_/g, " ")}
                  </Badge>
                  <div className="flex items-center gap-1 text-xs text-[var(--color-text-muted)]">
                    <Link2 className="h-3 w-3" />
                    {node.links?.length ?? node.linksCount ?? 0}
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-[var(--color-text-primary)] mb-1 line-clamp-2">
                  {node.title}
                </h3>
                {layers.l1Summary && (
                  <p className="text-xs text-[var(--color-text-muted)] italic line-clamp-2 mb-2">
                    {layers.l1Summary}
                  </p>
                )}
                <div className="flex flex-wrap gap-1">
                  {(node.tags || []).slice(0, 3).map((t) => (
                    <span key={t} className="text-[10px] text-brand-amber-light">
                      {t}
                    </span>
                  ))}
                </div>
                <div className="text-xs text-[var(--color-text-muted)] mt-2">
                  {formatDate(node.createdAt)}
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}

      {/* Detail modal */}
      {showDetail && selectedNode && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-16 px-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Node Detail</h2>
              <button
                onClick={() => {
                  setShowDetail(false);
                  setSelectedNode(null);
                }}
                className="p-1 rounded hover:bg-white/10 transition-colors"
              >
                <X className="h-4 w-4 text-[var(--color-text-muted)]" />
              </button>
            </div>
            <MemoryDetail
              node={selectedNode}
              onEdit={(id) => console.log("Edit", id)}
              onDelete={(id) => {
                useBrainStore.getState().deleteNode(id);
                setShowDetail(false);
                loadNodes();
              }}
              onNavigateToNode={(id) => {
                const node = nodes.find((n) => n.id === id);
                if (node) setSelectedNode(node);
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
