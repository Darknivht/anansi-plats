"use client";

import Link from "next/link";
import { MorningBriefing } from "../../../components/features/MorningBriefing";
import { QuickStats } from "../../../components/features/QuickStats";
import { ActivityFeed } from "../../../components/features/ActivityFeed";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardAction } from "../../../components/ui/GlassCard";
import { AnansiButton } from "../../../components/ui/AnansiButton";
import { BrainIcon } from "../../../components/ui/BrainIcon";
import { MessageCircle, Puzzle, Plug, GitBranch, Sparkles, ArrowRight } from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Your Second Brain overview for today
          </p>
        </div>
        <BrainIcon size={32} active glow="amber" />
      </div>

      {/* Morning Briefing */}
      <MorningBriefing />

      {/* Quick Stats */}
      <QuickStats />

      {/* Recent Activity + Quick Actions */}
      <div className="grid lg:grid-cols-3 gap-6">
        {/* Activity Feed (takes 2 columns) */}
        <div className="lg:col-span-2">
          <ActivityFeed />
        </div>

        {/* Quick Actions (takes 1 column) */}
        <div className="space-y-4">
          <GlassCard variant="base" padding="md">
            <GlassCardHeader>
              <GlassCardTitle>Quick Actions</GlassCardTitle>
            </GlassCardHeader>
            <div className="space-y-2">
              <Link href="/app/chat">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <MessageCircle className="h-5 w-5 text-brand-amber-light" />
                  <span className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors flex-1">
                    Chat with AI
                  </span>
                  <ArrowRight className="h-4 w-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)] transition-colors" />
                </div>
              </Link>
              <Link href="/app/agents">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <Puzzle className="h-5 w-5 text-brand-violet-light" />
                  <span className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors flex-1">
                    Create Agent
                  </span>
                  <ArrowRight className="h-4 w-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)] transition-colors" />
                </div>
              </Link>
              <Link href="/app/integrations">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <Plug className="h-5 w-5 text-semantic-info-light" />
                  <span className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors flex-1">
                    Connect Service
                  </span>
                  <ArrowRight className="h-4 w-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)] transition-colors" />
                </div>
              </Link>
              <Link href="/app/brain/graph">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
                  <GitBranch className="h-5 w-5 text-brand-teal-light" />
                  <span className="text-sm text-[var(--color-text-secondary)] group-hover:text-[var(--color-text-primary)] transition-colors flex-1">
                    Explore Second Brain
                  </span>
                  <ArrowRight className="h-4 w-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-text-primary)] transition-colors" />
                </div>
              </Link>
            </div>
          </GlassCard>

          {/* Brain Growth Card */}
          <GlassCard variant="elevated" glow="amber" padding="md">
            <div className="flex items-center gap-3 mb-3">
              <BrainIcon size={20} active glow="amber" />
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">Brain Stats</span>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Total nodes</span>
                <span className="text-[var(--color-text-primary)] font-semibold">47</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Total links</span>
                <span className="text-[var(--color-text-primary)] font-semibold">128</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Reviews due</span>
                <span className="text-brand-amber-light font-semibold">3</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[var(--color-text-muted)]">Hours saved</span>
                <span className="text-semantic-success-light font-semibold">12.5</span>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
