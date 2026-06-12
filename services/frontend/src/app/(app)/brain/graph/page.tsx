"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useBrainStore } from "@/stores/brain";
import { MemoryGraph } from "@/components/brain/MemoryGraph";
import { MemoryDetail } from "@/components/brain/MemoryDetail";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/GlassCard";
import { Input } from "@/components/ui/Input";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Badge } from "@/components/ui/Badge";
import { BrainIcon } from "@/components/ui/BrainIcon";
import type { MemoryNode } from "@/types";
import {
  Search,
  SlidersHorizontal,
  X,
  ChevronLeft,
  GitBranch,
  Network,
  Tag,
  Layers,
  RefreshCw,
  Maximize2,
  Minimize2,
} from "lucide-react";

export default function BrainGraphPage() {
  const {
    graphData,
    isLoadingGraph,
    selectedNodeId,
    selectedNodeDetail,
    loadGraph,
    loadLocalGraph,
    localGraphData,
    selectNode,
    loadNodeDetail,
    createLink,
    searchNodes,
    searchResults,
    isSearching,
    setFilter,
    filters,
  } = useBrainStore();

  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchPanel, setShowSearchPanel] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [showDetail, setShowDetail] = useState(false);
  const [localMode, setLocalMode] = useState(false);
  const [localDepth, setLocalDepth] = useState(2);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [selectedType, setSelectedType] = useState<string | null>(null);

  // Load full graph on mount
  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Handle node click
  const handleNodeClick = useCallback(
    (nodeId: string) => {
      selectNode(nodeId);
      setShowDetail(true);
    },
    [selectNode],
  );

  const handleNodeHover = useCallback((nodeId: string | null) => {
    // Could add highlight effects
  }, []);

  const handleLinkCreate = useCallback(
    (sourceId: string, targetId: string) => {
      createLink(sourceId, targetId);
    },
    [createLink],
  );

  // Search
  const handleSearch = useCallback(() => {
    if (searchQuery.trim()) {
      searchNodes(
        searchQuery,
        selectedTag ? [selectedTag] : undefined,
        selectedType ? [selectedType] : undefined,
      );
      setShowSearchPanel(true);
    }
  }, [searchQuery, selectedTag, selectedType, searchNodes]);

  // Extract unique tags
  const allTags = useMemo(() => {
    if (!graphData?.nodes) return [];
    const tagSet = new Set<string>();
    graphData.nodes.forEach((n) => n.tags.forEach((t) => tagSet.add(t)));
    return Array.from(tagSet).sort();
  }, [graphData]);

  // Graph data to display
  const displayGraph = localMode && localGraphData ? localGraphData : graphData;

  return (
    <div className="h-[calc(100vh-6rem)] flex flex-col">
      {/* Top bar */}
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-heading font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <Network className="h-5 w-5 text-brand-amber-light" />
            Graph View
          </h1>
          <div className="flex items-center gap-1.5 text-xs text-[var(--color-text-muted)]">
            <span>{graphData?.nodes.length ?? 0} nodes</span>
            <span>·</span>
            <span>{graphData?.edges.length ?? 0} edges</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {selectedNodeId && (
            <>
              <AnansiButton
                variant="ghost"
                size="sm"
                onClick={() => {
                  if (localMode) {
                    setLocalMode(false);
                  } else {
                    loadLocalGraph(selectedNodeId, localDepth);
                    setLocalMode(true);
                  }
                }}
              >
                <GitBranch className="h-4 w-4" />
                {localMode ? "Global View" : "Focus View"}
              </AnansiButton>
              {localMode && (
                <select
                  value={localDepth}
                  onChange={(e) => {
                    const d = parseInt(e.target.value);
                    setLocalDepth(d);
                    if (selectedNodeId) loadLocalGraph(selectedNodeId, d);
                  }}
                  className="bg-transparent text-xs text-[var(--color-text-muted)] border border-[var(--color-border-subtle)] rounded px-1.5 py-1"
                >
                  <option value={1}>Depth 1</option>
                  <option value={2}>Depth 2</option>
                  <option value={3}>Depth 3</option>
                </select>
              )}
            </>
          )}
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => {
              loadGraph();
              setLocalMode(false);
            }}
          >
            <RefreshCw className="h-4 w-4" />
          </AnansiButton>
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal className="h-4 w-4" />
          </AnansiButton>
          <AnansiButton
            variant="ghost"
            size="sm"
            onClick={() => setShowSearchPanel(!showSearchPanel)}
          >
            <Search className="h-4 w-4" />
          </AnansiButton>
        </div>
      </div>

      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Search panel */}
        {showSearchPanel && (
          <div className="w-72 shrink-0 overflow-y-auto">
            <GlassCard variant="base" padding="sm" className="h-full">
              <div className="space-y-3 p-2">
                <Input
                  placeholder="Search nodes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                  icon={<Search className="h-4 w-4" />}
                />
                <AnansiButton
                  variant="primary"
                  size="sm"
                  fullWidth
                  onClick={handleSearch}
                  feedbackState={isSearching ? "loading" : "idle"}
                >
                  Search
                </AnansiButton>

                {searchResults.length > 0 && (
                  <div className="space-y-1 mt-3">
                    <p className="text-xs text-[var(--color-text-muted)] mb-2">Results</p>
                    {searchResults.map((node) => (
                      <button
                        key={node.id}
                        onClick={() => {
                          selectNode(node.id);
                          setShowDetail(true);
                          loadLocalGraph(node.id, localDepth);
                          setLocalMode(true);
                        }}
                        className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 transition-colors text-sm"
                      >
                        <div className="font-medium text-[var(--color-text-primary)] truncate">
                          {node.title}
                        </div>
                        <div className="text-xs text-[var(--color-text-muted)]">
                          {node.type} · {node.tags.slice(0, 2).join(", ")}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </GlassCard>
          </div>
        )}

        {/* Graph area */}
        <div className="flex-1 min-w-0">
          <GlassCard variant="base" padding="sm" className="h-full">
            {isLoadingGraph ? (
              <div className="h-full flex items-center justify-center">
                <div className="animate-pulse text-[var(--color-text-muted)]">Loading graph...</div>
              </div>
            ) : displayGraph ? (
              <MemoryGraph
                nodes={displayGraph.nodes}
                edges={displayGraph.edges}
                onNodeClick={handleNodeClick}
                onNodeHover={handleNodeHover}
                onLinkCreate={handleLinkCreate}
                selectedNodeId={selectedNodeId}
                filters={{
                  tags: selectedTag ? [selectedTag] : undefined,
                  types: selectedType ? [selectedType] : undefined,
                }}
                showLabels
                interactive
                className="w-full h-full"
              />
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-[var(--color-text-muted)]">No data found</p>
              </div>
            )}
          </GlassCard>
        </div>

        {/* Detail panel */}
        {showDetail && selectedNodeDetail && (
          <div className="w-96 shrink-0 overflow-y-auto">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">Node Detail</h2>
              <button
                onClick={() => {
                  setShowDetail(false);
                  selectNode(null);
                }}
                className="p-1 rounded hover:bg-white/10 transition-colors"
              >
                <X className="h-4 w-4 text-[var(--color-text-muted)]" />
              </button>
            </div>
            <MemoryDetail
              node={selectedNodeDetail}
              onDelete={(id) => {
                useBrainStore.getState().deleteNode(id);
                setShowDetail(false);
              }}
              onCreateLink={(id) => {
                // Enable link creation mode
              }}
            />
          </div>
        )}

        {/* Filter panel */}
        {showFilters && (
          <div className="w-56 shrink-0 overflow-y-auto">
            <GlassCard variant="base" padding="sm">
              <div className="space-y-4 p-2">
                <div>
                  <p className="text-xs text-[var(--color-text-muted)] font-semibold mb-2 flex items-center gap-1">
                    <Tag className="h-3 w-3" />
                    Tags
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {allTags.slice(0, 20).map((tag) => (
                      <button
                        key={tag}
                        onClick={() => setSelectedTag(selectedTag === tag ? null : tag)}
                        className={`text-xs px-2 py-1 rounded-full transition-colors ${
                          selectedTag === tag
                            ? "bg-brand-amber/20 text-brand-amber-light border border-brand-amber/30"
                            : "bg-white/5 text-[var(--color-text-muted)] border border-transparent hover:border-[var(--color-border-subtle)]"
                        }`}
                      >
                        {tag.replace("#", "")}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <p className="text-xs text-[var(--color-text-muted)] font-semibold mb-2 flex items-center gap-1">
                    <Layers className="h-3 w-3" />
                    Types
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {["fact", "preference", "pattern", "relation"].map((type) => (
                      <button
                        key={type}
                        onClick={() => setSelectedType(selectedType === type ? null : type)}
                        className={`text-xs px-2 py-1 rounded-full transition-colors capitalize ${
                          selectedType === type
                            ? "bg-brand-violet/20 text-brand-violet-light border border-brand-violet/30"
                            : "bg-white/5 text-[var(--color-text-muted)] border border-transparent hover:border-[var(--color-border-subtle)]"
                        }`}
                      >
                        {type}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </GlassCard>
          </div>
        )}
      </div>
    </div>
  );
}
