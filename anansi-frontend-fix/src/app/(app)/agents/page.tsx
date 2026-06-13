/**
 * Agent Library Page — Grid/list view of user's agents.
 *
 * Shows agent cards with status badges, search/filter, create button,
 * and agent actions (run, pause, edit, duplicate, delete).
 */

"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  Play,
  Pause,
  Edit3,
  Copy,
  Trash2,
  Layers,
  TrendingUp,
} from "lucide-react";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent, GlassCardAction } from "../../../components/ui/GlassCard";
import { AnansiButton } from "../../../components/ui/AnansiButton";
import { Badge } from "../../../components/ui/Badge";
import { Skeleton } from "../../../components/ui/Skeleton";
import { Input } from "../../../components/ui/Input";
import { cn } from "../../../lib/utils";
import { api } from "../../../lib/api";
import type { Agent } from "../../../types";

// ── Status badge config ────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; variant: "success" | "warning" | "error" | "info" | "brand" }> = {
  draft: { label: "Draft", variant: "brand" },
  active: { label: "Active", variant: "success" },
  paused: { label: "Paused", variant: "warning" },
  archived: { label: "Archived", variant: "error" },
};

// ── Page ────────────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const params: Record<string, string | number | boolean | undefined> = {
        page,
        per_page: 20,
      };
      if (search) params.search = search;
      if (statusFilter) params.status = statusFilter;

      const result = await api.get<{
        items: Agent[];
        total: number;
        page: number;
        per_page: number;
        pages: number;
      }>("/api/v1/agents", { params });

      setAgents(result.items);
      setTotalPages(result.pages);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
    } finally {
      setLoading(false);
    }
  }, [page, search, statusFilter]);

  useEffect(() => {
    fetchAgents();
  }, [fetchAgents]);

  // ── Actions ─────────────────────────────────────────────────────────────────

  const handleRun = async (agentId: string) => {
    try {
      await api.post(`/api/v1/agents/${agentId}/run`);
      fetchAgents();
    } catch (err) {
      console.error("Failed to run agent:", err);
    }
  };

  const handlePauseToggle = async (agent: Agent) => {
    try {
      await api.patch(`/api/v1/agents/${agent.id}`, {
        status: agent.status === "active" ? "paused" : "active",
      });
      fetchAgents();
    } catch (err) {
      console.error("Failed to toggle agent status:", err);
    }
  };

  const handleDuplicate = async (agentId: string) => {
    try {
      await api.post(`/api/v1/agents/${agentId}/duplicate`);
      fetchAgents();
    } catch (err) {
      console.error("Failed to duplicate agent:", err);
    }
  };

  const handleDelete = async (agentId: string) => {
    if (!window.confirm("Are you sure you want to archive this agent?")) return;
    try {
      await api.delete(`/api/v1/agents/${agentId}`);
      fetchAgents();
    } catch (err) {
      console.error("Failed to delete agent:", err);
    }
  };

  // ── Filter statuses ─────────────────────────────────────────────────────────

  const statuses = ["", "draft", "active", "paused", "archived"];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            Agents
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Create and manage your AI agents
          </p>
        </div>
        <AnansiButton
          variant="primary"
          size="lg"
          icon={<Plus className="h-5 w-5" />}
          onClick={() => router.push("/agents/new")}
        >
          Create Agent
        </AnansiButton>
      </div>

      {/* Search + Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-text-muted)]" />
          <Input
            placeholder="Search agents..."
            className="pl-10"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>
        <div className="flex gap-2">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => {
                setStatusFilter(s);
                setPage(1);
              }}
              className={cn(
                "px-3 py-1.5 rounded-lg text-sm font-medium transition-all",
                statusFilter === s
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] border border-transparent hover:border-[var(--color-border-subtle)]"
              )}
            >
              {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"}
            </button>
          ))}
        </div>
      </div>

      {/* Agent Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <GlassCard key={i} variant="base">
              <Skeleton className="h-6 w-3/4 mb-3" />
              <Skeleton className="h-4 w-full mb-2" />
              <Skeleton className="h-4 w-1/2 mb-4" />
              <div className="flex gap-2">
                <Skeleton className="h-8 w-16" />
                <Skeleton className="h-8 w-16" />
              </div>
            </GlassCard>
          ))}
        </div>
      ) : agents.length === 0 ? (
        <EmptyState onCreate={() => router.push("/agents/new")} />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {agents.map((agent) => {
              const statusCfg = STATUS_CONFIG[agent.status] || STATUS_CONFIG.draft;
              const blockCount = agent.definition?.blocks?.length || 0;

              return (
                <GlassCard
                  key={agent.id}
                  variant="interactive"
                  glow="none"
                  className="group relative"
                >
                  <GlassCardHeader>
                    <div className="flex items-center gap-2 min-w-0">
                      <GlassCardTitle className="truncate">
                        {agent.name}
                      </GlassCardTitle>
                      <Badge variant={statusCfg.variant}>
                        {statusCfg.label}
                      </Badge>
                    </div>
                  </GlassCardHeader>

                  <GlassCardContent>
                    <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2 min-h-[2.5rem]">
                      {agent.description || "No description"}
                    </p>

                    <div className="flex items-center gap-4 mt-4 text-xs text-[var(--color-text-muted)]">
                      <span className="flex items-center gap-1">
                        <Layers className="h-3.5 w-3.5" />
                        {blockCount} blocks
                      </span>
                      <span className="flex items-center gap-1">
                        <TrendingUp className="h-3.5 w-3.5" />
                        {agent.totalRuns} runs
                      </span>
                      {agent.successRate > 0 && (
                        <span className={cn(
                          "font-medium",
                          agent.successRate >= 0.8
                            ? "text-semantic-success"
                            : agent.successRate >= 0.5
                            ? "text-semantic-warning"
                            : "text-semantic-error"
                        )}>
                          {(agent.successRate * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                  </GlassCardContent>

                  {/* Actions */}
                  <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[var(--color-border-subtle)]">
                    <button
                      onClick={() => handleRun(agent.id)}
                      className="p-2 rounded-lg hover:bg-amber-500/10 text-[var(--color-text-muted)] hover:text-amber-400 transition-colors"
                      title="Run agent"
                    >
                      <Play className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handlePauseToggle(agent)}
                      className="p-2 rounded-lg hover:bg-teal-500/10 text-[var(--color-text-muted)] hover:text-teal-400 transition-colors"
                      title={agent.status === "active" ? "Pause" : "Activate"}
                    >
                      <Pause className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => router.push(`/agents/${agent.id}`)}
                      className="p-2 rounded-lg hover:bg-violet-500/10 text-[var(--color-text-muted)] hover:text-violet-400 transition-colors"
                      title="Edit"
                    >
                      <Edit3 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDuplicate(agent.id)}
                      className="p-2 rounded-lg hover:bg-blue-500/10 text-[var(--color-text-muted)] hover:text-blue-400 transition-colors"
                      title="Duplicate"
                    >
                      <Copy className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(agent.id)}
                      className="p-2 rounded-lg hover:bg-red-500/10 text-[var(--color-text-muted)] hover:text-red-400 transition-colors ml-auto"
                      title="Archive"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </GlassCard>
              );
            })}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-8">
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  onClick={() => setPage(i + 1)}
                  className={cn(
                    "w-8 h-8 rounded-lg text-sm font-medium transition-all",
                    page === i + 1
                      ? "bg-amber-500/20 text-amber-400"
                      : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                  )}
                >
                  {i + 1}
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Empty State ─────────────────────────────────────────────────────────────────

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 flex items-center justify-center mb-6">
        <Layers className="h-8 w-8 text-amber-400" />
      </div>
      <h3 className="text-xl font-heading font-bold text-[var(--color-text-primary)] mb-2">
        No agents yet
      </h3>
      <p className="text-sm text-[var(--color-text-muted)] mb-8 text-center max-w-md">
        Create your first AI agent to automate tasks, process data, and connect your services.
      </p>
      <AnansiButton
        variant="primary"
        size="lg"
        icon={<Plus className="h-5 w-5" />}
        onClick={onCreate}
      >
        Create Your First Agent
      </AnansiButton>
    </div>
  );
}
