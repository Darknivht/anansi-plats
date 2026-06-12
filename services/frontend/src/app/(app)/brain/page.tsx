"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useBrainStore } from "@/stores/brain";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Badge } from "@/components/ui/Badge";
import { BrainIcon } from "@/components/ui/BrainIcon";
import {
  Layers,
  Link2,
  Share2,
  AlertTriangle,
  TrendingUp,
  GitBranch,
  Brain,
  Calendar,
  RefreshCw,
  Tag,
  Zap,
  Download,
  ChevronRight,
  BarChart3,
  Activity,
  Network,
} from "lucide-react";

export default function BrainOverviewPage() {
  const { stats, loadStats, reviewQueue, loadReviewQueue } = useBrainStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function load() {
      await Promise.all([loadStats(), loadReviewQueue()]);
      setIsLoading(false);
    }
    load();
  }, [loadStats, loadReviewQueue]);

  if (isLoading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 rounded bg-white/5" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 rounded-lg bg-white/5" />
          ))}
        </div>
        <div className="h-64 rounded-lg bg-white/5" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <BrainIcon size={28} active glow="amber" />
            Second Brain
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Your interconnected knowledge web
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link href="/app/brain/nodes">
            <AnansiButton variant="secondary" size="sm">
              <Layers className="h-4 w-4" />
              New Node
            </AnansiButton>
          </Link>
          <Link href="/app/brain/daily">
            <AnansiButton variant="secondary" size="sm">
              <Calendar className="h-4 w-4" />
              Daily Note
            </AnansiButton>
          </Link>
        </div>
      </div>

      {/* Health Score + Quick Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <GlassCard variant="base" glow="amber" padding="md">
          <div className="flex items-center gap-2 mb-1">
            <Brain className="h-4 w-4 text-brand-amber-light" />
            <span className="text-xs text-[var(--color-text-muted)]">Total Nodes</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {stats?.totalNodes ?? 0}
          </p>
        </GlassCard>

        <GlassCard variant="base" glow="teal" padding="md">
          <div className="flex items-center gap-2 mb-1">
            <Link2 className="h-4 w-4 text-brand-teal-light" />
            <span className="text-xs text-[var(--color-text-muted)]">Total Links</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {stats?.totalLinks ?? 0}
          </p>
        </GlassCard>

        <GlassCard variant="base" glow="violet" padding="md">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="h-4 w-4 text-brand-violet-light" />
            <span className="text-xs text-[var(--color-text-muted)]">Density</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {((stats?.graphDensity ?? 0) * 100).toFixed(1)}%
          </p>
        </GlassCard>

        <GlassCard variant="base" glow="amber" padding="md">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="h-4 w-4 text-semantic-success-light" />
            <span className="text-xs text-[var(--color-text-muted)]">Health Score</span>
          </div>
          <p className="text-2xl font-bold text-[var(--color-text-primary)]">
            {((stats?.healthScore ?? 0) * 100).toFixed(0)}%
          </p>
        </GlassCard>
      </div>

      {/* Main content grid */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Left column (2 cols) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Graph Preview */}
          <Link href="/app/brain/graph">
            <GlassCard variant="interactive" glow="amber" padding="md">
              <GlassCardHeader>
                <GlassCardTitle>
                  <div className="flex items-center gap-2">
                    <Network className="h-5 w-5 text-brand-amber-light" />
                    Graph View
                  </div>
                </GlassCardTitle>
                <ChevronRight className="h-4 w-4 text-[var(--color-text-muted)]" />
              </GlassCardHeader>
              <GlassCardContent>
                <div className="h-40 rounded-lg bg-gradient-to-br from-brand-amber/5 via-brand-violet/5 to-brand-teal/5 flex items-center justify-center border border-[var(--color-border-subtle)]">
                  <div className="text-center">
                    <GitBranch className="h-10 w-10 text-brand-amber/40 mx-auto mb-2" />
                    <p className="text-sm text-[var(--color-text-muted)]">
                      {stats?.totalNodes ?? 0} nodes · {stats?.totalLinks ?? 0} connections
                    </p>
                    <p className="text-xs text-[var(--color-text-muted)] mt-1">
                      Click to explore your knowledge web
                    </p>
                  </div>
                </div>
              </GlassCardContent>
            </GlassCard>
          </Link>

          {/* Weekly Growth */}
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-semantic-success-light" />
                  Weekly Growth
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {stats?.weeklyGrowth?.newNodes ?? 0}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">New Nodes</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {stats?.weeklyGrowth?.newLinks ?? 0}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">New Links</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold text-[var(--color-text-primary)]">
                    {stats?.weeklyGrowth?.reviewsCompleted ?? 0}
                  </p>
                  <p className="text-xs text-[var(--color-text-muted)]">Reviews</p>
                </div>
              </div>
            </GlassCardContent>
          </GlassCard>

          {/* Suggested Links */}
          <GlassCard variant="base" glow="teal" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <Zap className="h-5 w-5 text-brand-teal-light" />
                  Suggested Connections
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              {stats && stats.orphanCount > 0 ? (
                <div>
                  <p className="text-sm text-[var(--color-text-muted)] mb-3">
                    I found <span className="text-brand-amber-light font-semibold">{stats.orphanCount}</span> orphan
                    nodes that could use more connections.
                  </p>
                  <Link href="/app/brain/graph">
                    <AnansiButton variant="secondary" size="sm">
                      Show orphan nodes
                    </AnansiButton>
                  </Link>
                </div>
              ) : (
                <p className="text-sm text-[var(--color-text-muted)]">
                  Your knowledge web is well-connected! No orphan nodes to suggest.
                </p>
              )}
            </GlassCardContent>
          </GlassCard>
        </div>

        {/* Right column (1 col) */}
        <div className="space-y-6">
          {/* Review Queue */}
          <GlassCard variant="base" glow="amber" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <RefreshCw className="h-4 w-4 text-brand-amber-light" />
                  Review Queue
                </div>
              </GlassCardTitle>
              <Badge variant={reviewQueue.length > 0 ? "warning" : "success"} size="sm" pill>
                {reviewQueue.length} due
              </Badge>
            </GlassCardHeader>
            <GlassCardContent>
              {reviewQueue.length > 0 ? (
                <div className="space-y-3">
                  <div className="text-sm text-[var(--color-text-muted)]">
                    You have <span className="text-brand-amber-light font-semibold">{reviewQueue.length}</span> memories
                    due for review.
                  </div>
                  <Link href="/app/brain/review">
                    <AnansiButton variant="primary" size="md" fullWidth>
                      Start Review
                    </AnansiButton>
                  </Link>
                </div>
              ) : (
                <div className="text-center py-4">
                  <div className="text-3xl mb-1">✓</div>
                  <p className="text-sm text-[var(--color-text-muted)]">All caught up!</p>
                  <p className="text-xs text-[var(--color-text-muted)] mt-1">No reviews due right now.</p>
                </div>
              )}
            </GlassCardContent>
          </GlassCard>

          {/* Tag Cloud */}
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <Tag className="h-4 w-4 text-brand-violet-light" />
                  Tags
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              <div className="flex flex-wrap gap-2">
                {(stats?.tags ?? []).slice(0, 15).map((t) => (
                  <Link key={t.tag} href={`/app/brain/nodes?tag=${encodeURIComponent(t.tag)}`}>
                    <Badge variant="brand" size="md" pill className="cursor-pointer hover:bg-brand-amber/20 transition-colors">
                      <Tag className="h-3 w-3" />
                      {t.tag.replace("#", "")}
                      <span className="ml-1 text-[10px] opacity-70">{t.count}</span>
                    </Badge>
                  </Link>
                ))}
                {(stats?.tags ?? []).length === 0 && (
                  <p className="text-sm text-[var(--color-text-muted)]">No tags yet</p>
                )}
              </div>
            </GlassCardContent>
          </GlassCard>

          {/* Orphans */}
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-semantic-warning-light" />
                  Orphans
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              <p className="text-3xl font-bold text-[var(--color-text-primary)] mb-1">
                {stats?.orphanCount ?? 0}
              </p>
              <p className="text-xs text-[var(--color-text-muted)]">
                Nodes with fewer than 2 connections
              </p>
            </GlassCardContent>
          </GlassCard>

          {/* Export */}
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>
                <div className="flex items-center gap-2">
                  <Download className="h-4 w-4 text-brand-teal-light" />
                  Export
                </div>
              </GlassCardTitle>
            </GlassCardHeader>
            <GlassCardContent>
              <Link href="/app/brain/nodes?export=obsidian">
                <AnansiButton variant="secondary" size="sm" fullWidth>
                  <Download className="h-4 w-4" />
                  Export as Obsidian Vault
                </AnansiButton>
              </Link>
            </GlassCardContent>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
