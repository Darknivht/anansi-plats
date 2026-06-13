"use client";

import { cn } from "../../lib/utils";
import { GlassCard } from "../../components/ui/GlassCard";
import { Brain, Bot, CheckCircle, Zap } from "lucide-react";

interface Stat {
  icon: React.ReactNode;
  label: string;
  value: string;
  trend?: string;
  trendUp?: boolean;
}

interface QuickStatsProps {
  className?: string;
}

const stats: Stat[] = [
  {
    icon: <Brain className="h-5 w-5" />,
    label: "Brain Growth",
    value: "47 nodes",
    trend: "+12 this week",
    trendUp: true,
  },
  {
    icon: <Bot className="h-5 w-5" />,
    label: "Active Agents",
    value: "3",
    trend: "All running",
    trendUp: true,
  },
  {
    icon: <CheckCircle className="h-5 w-5" />,
    label: "Tasks Today",
    value: "7 / 9",
    trend: "78% done",
    trendUp: true,
  },
  {
    icon: <Zap className="h-5 w-5" />,
    label: "Hours Saved",
    value: "12.5",
    trend: "+3.2 this week",
    trendUp: true,
  },
];

/**
 * Quick Stats row for the dashboard — brain growth, active agents,
 * tasks completed, and hours saved.
 */
export function QuickStats({ className }: QuickStatsProps) {
  return (
    <div
      className={cn(
        "grid grid-cols-2 lg:grid-cols-4 gap-4",
        className,
      )}
    >
      {stats.map((stat) => (
        <GlassCard
          key={stat.label}
          variant="base"
          padding="md"
          className="flex flex-col gap-2"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
              {stat.label}
            </span>
            <span className="text-[var(--color-text-muted)]">{stat.icon}</span>
          </div>
          <span className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">
            {stat.value}
          </span>
          {stat.trend && (
            <span
              className={cn(
                "text-xs",
                stat.trendUp
                  ? "text-semantic-success-light"
                  : "text-semantic-warning-light",
              )}
            >
              {stat.trend}
            </span>
          )}
        </GlassCard>
      ))}
    </div>
  );
}
