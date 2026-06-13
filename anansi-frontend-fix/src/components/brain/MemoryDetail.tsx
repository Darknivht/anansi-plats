"use client";

import { useState } from "react";
import { cn } from "../../lib/utils";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "../../components/ui/GlassCard";
import { Badge } from "../../components/ui/Badge";
import { AnansiButton } from "../../components/ui/AnansiButton";
import type { MemoryNode, MemoryLink } from "../../types";
import {
  Edit3,
  Trash2,
  Link2,
  Plus,
  Calendar,
  Clock,
  Activity,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Brain,
  Tag,
  Layers,
  RefreshCw,
} from "lucide-react";

// ─── Types ──────────────────────────────────────────────────────────────────────

interface MemoryDetailProps {
  node: MemoryNode;
  onEdit?: (nodeId: string, data: Partial<MemoryNode>) => void;
  onDelete?: (nodeId: string) => void;
  onCreateLink?: (nodeId: string) => void;
  onScheduleReview?: (nodeId: string) => void;
  onExport?: (nodeId: string) => void;
  onNavigateToNode?: (nodeId: string) => void;
  className?: string;
}

// ─── Format helpers ─────────────────────────────────────────────────────────────

function formatDate(isoString: string | undefined | null): string {
  if (!isoString) return "—";
  try {
    const date = new Date(isoString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return isoString;
  }
}

function timeUntil(isoString: string | undefined | null): string {
  if (!isoString) return "—";
  try {
    const now = new Date();
    const target = new Date(isoString);
    const diffMs = target.getTime() - now.getTime();
    if (diffMs <= 0) return "Overdue";
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    if (hours < 24) return `${hours}h`;
    const days = Math.floor(hours / 24);
    return `${days}d`;
  } catch {
    return "—";
  }
}

function formatInterval(seconds: number): string {
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
}

// ─── Component ───────────────────────────────────────────────────────────────────

export function MemoryDetail({
  node,
  onEdit,
  onDelete,
  onCreateLink,
  onScheduleReview,
  onExport,
  onNavigateToNode,
  className,
}: MemoryDetailProps) {
  const [showLayers, setShowLayers] = useState(false);
  const [showAllLinks, setShowAllLinks] = useState(false);

  const metadata = node.metadata || {};
  const layers = node.layers;
  const links = node.links || [];
  const incomingLinks = links.filter((l) => l.direction === "incoming");
  const outgoingLinks = links.filter((l) => l.direction === "outgoing");

  const displayLinks = showAllLinks ? links : links.slice(0, 10);
  const linkCount = links.length;

  return (
    <GlassCard variant="elevated" className={cn("overflow-hidden", className)}>
      {/* Header */}
      <GlassCardHeader>
        <div className="flex items-center gap-2 min-w-0">
          <Brain className="h-5 w-5 text-brand-amber-light shrink-0" />
          <GlassCardTitle className="truncate">{node.title}</GlassCardTitle>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge variant="brand" size="sm">
            {node.type.replace("_", " ")}
          </Badge>
          {node.isFinalized !== undefined && (
            <Badge variant={node.isFinalized ? "success" : "warning"} size="sm">
              {node.isFinalized ? "Finalized" : "Draft"}
            </Badge>
          )}
        </div>
      </GlassCardHeader>

      <GlassCardContent className="space-y-5">
        {/* Tags */}
        {node.tags && node.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {node.tags.map((tag) => (
              <Badge key={tag} variant="brand" size="sm" pill>
                <Tag className="h-3 w-3" />
                {tag.replace("#", "")}
              </Badge>
            ))}
          </div>
        )}

        {/* Content */}
        <div className="text-sm text-[var(--color-text-primary)] leading-relaxed whitespace-pre-wrap">
          {node.content}
        </div>

        {/* Progressive Summarization Layers */}
        {layers && (layers.l1Summary || layers.l2Highlights || layers.l4Compressed) && (
          <div>
            <button
              onClick={() => setShowLayers(!showLayers)}
              className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)] hover:text-brand-amber-light transition-colors"
            >
              <Layers className="h-4 w-4" />
              <span>Progressive Summarization</span>
              {showLayers ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
            </button>

            {showLayers && (
              <div className="mt-3 space-y-3 pl-6 border-l border-[var(--color-border-subtle)]">
                {layers.l1Summary && (
                  <div>
                    <div className="text-xs text-brand-amber-light font-semibold mb-1">L1 · Summary</div>
                    <p className="text-sm text-[var(--color-text-secondary)] italic">
                      "{layers.l1Summary}"
                    </p>
                  </div>
                )}

                {layers.l2Highlights && layers.l2Highlights.length > 0 && (
                  <div>
                    <div className="text-xs text-brand-violet-light font-semibold mb-1">L2 · Highlights</div>
                    <ul className="space-y-1">
                      {layers.l2Highlights.map((h, i) => (
                        <li key={i} className="text-sm text-[var(--color-text-secondary)]">
                          <span className="font-medium text-[var(--color-text-primary)]">{h}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {layers.l4Compressed && (
                  <div>
                    <div className="text-xs text-brand-teal-light font-semibold mb-1">L4 · Compressed</div>
                    <p className="text-sm text-[var(--color-text-secondary)]">{layers.l4Compressed}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Links Section */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
              <Link2 className="h-4 w-4" />
              <span>Links ({linkCount})</span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {incomingLinks.length} incoming · {outgoingLinks.length} outgoing
              </span>
            </div>
            {onCreateLink && (
              <AnansiButton variant="ghost" size="sm" onClick={() => onCreateLink(node.id)}>
                <Plus className="h-3.5 w-3.5" />
                Add Link
              </AnansiButton>
            )}
          </div>

          {displayLinks.length > 0 ? (
            <div className="space-y-1.5">
              {displayLinks.map((link) => {
                const isIncoming = link.direction === "incoming";
                const linkedTitle = isIncoming
                  ? (link as MemoryLink & { sourceTitle?: string }).sourceTitle || "Unknown"
                  : (link as MemoryLink & { targetTitle?: string }).targetTitle || "Unknown";
                const linkedId = isIncoming ? link.sourceId : link.targetId;

                return (
                  <div
                    key={link.id}
                    className="flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors group"
                  >
                    <div
                      className={cn(
                        "w-1.5 h-1.5 rounded-full shrink-0",
                        isIncoming ? "bg-brand-teal-light" : "bg-brand-amber-light",
                      )}
                    />
                    <span className="text-xs text-[var(--color-text-muted)] shrink-0">
                      {isIncoming ? "←" : "→"}
                    </span>
                    <button
                      onClick={() => onNavigateToNode?.(linkedId)}
                      className="text-sm text-[var(--color-text-primary)] hover:text-brand-amber-light truncate flex-1 text-left"
                    >
                      {linkedTitle}
                    </button>
                    <span className="text-xs text-[var(--color-text-muted)] shrink-0">
                      {link.linkType.replace(/_/g, " ")}
                    </span>
                    {link.label && (
                      <span className="text-xs text-[var(--color-text-muted)] hidden sm:inline truncate max-w-[120px]">
                        · {link.label}
                      </span>
                    )}
                    <ExternalLink className="h-3 w-3 text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                  </div>
                );
              })}

              {linkCount > 10 && !showAllLinks && (
                <button
                  onClick={() => setShowAllLinks(true)}
                  className="text-xs text-brand-amber-light hover:text-brand-amber px-3 py-1"
                >
                  Show all {linkCount} links
                </button>
              )}
            </div>
          ) : (
            <p className="text-sm text-[var(--color-text-muted)] italic">
              No links yet. This is an orphan node.
            </p>
          )}
        </div>

        {/* Review Info */}
        <div className="flex flex-wrap items-center gap-4 text-xs text-[var(--color-text-muted)]">
          <div className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            <span>Interval: {formatInterval(node.reviewInterval)}</span>
          </div>
          {node.lastReviewedAt && (
            <div className="flex items-center gap-1.5">
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Last reviewed: {formatDate(node.lastReviewedAt)}</span>
            </div>
          )}
          {node.nextReviewAt && (
            <div className="flex items-center gap-1.5">
              <Calendar className="h-3.5 w-3.5" />
              <span>
                Next review: {formatDate(node.nextReviewAt)}
                {timeUntil(node.nextReviewAt) !== "—" && (
                  <span className="ml-1 text-brand-amber-light">({timeUntil(node.nextReviewAt)})</span>
                )}
              </span>
            </div>
          )}
          <div className="flex items-center gap-1.5">
            <Activity className="h-3.5 w-3.5" />
            <span>Accessed {metadata.accessCount || 0} times</span>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-[var(--color-text-muted)]">
          <span>Source: {metadata.source || node.source || "unknown"}</span>
          <span>Confidence: {(metadata.confidence || node.confidence || 0) * 100}%</span>
          <span>Created: {formatDate(node.createdAt)}</span>
          <span>Updated: {formatDate(node.updatedAt)}</span>
          {node.paraCategory && <span>PARA: {node.paraCategory}</span>}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-[var(--color-border-subtle)]">
          {onEdit && (
            <AnansiButton variant="secondary" size="sm" onClick={() => onEdit(node.id, {})}>
              <Edit3 className="h-3.5 w-3.5" />
              Edit
            </AnansiButton>
          )}
          {onScheduleReview && (
            <AnansiButton variant="secondary" size="sm" onClick={() => onScheduleReview(node.id)}>
              <RefreshCw className="h-3.5 w-3.5" />
              Review
            </AnansiButton>
          )}
          {onExport && (
            <AnansiButton variant="ghost" size="sm" onClick={() => onExport(node.id)}>
              <ExternalLink className="h-3.5 w-3.5" />
              Export
            </AnansiButton>
          )}
          {onDelete && (
            <AnansiButton variant="ghost" size="sm" onClick={() => onDelete(node.id)}>
              <Trash2 className="h-3.5 w-3.5 text-semantic-error" />
            </AnansiButton>
          )}
        </div>
      </GlassCardContent>
    </GlassCard>
  );
}
