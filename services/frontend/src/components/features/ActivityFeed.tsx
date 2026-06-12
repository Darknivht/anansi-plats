"use client";

import { cn } from "@/lib/utils";
import { GlassCard, GlassCardHeader, GlassCardTitle } from "@/components/ui/GlassCard";
import { Bot, Brain, Link, MessageCircle, Webhook, Zap } from "lucide-react";

interface Activity {
  id: string;
  type: "agent_run" | "ai_conversation" | "integration" | "brain_link" | "brain_node";
  title: string;
  description: string;
  timestamp: string;
  status?: "success" | "error" | "pending";
}

const activityIcons: Record<Activity["type"], React.ReactNode> = {
  agent_run: <Bot className="h-4 w-4" />,
  ai_conversation: <MessageCircle className="h-4 w-4" />,
  integration: <Webhook className="h-4 w-4" />,
  brain_link: <Link className="h-4 w-4" />,
  brain_node: <Brain className="h-4 w-4" />,
};

const activityColors: Record<Activity["type"], string> = {
  agent_run: "text-violet-400",
  ai_conversation: "text-amber-400",
  integration: "text-blue-400",
  brain_link: "text-teal-400",
  brain_node: "text-amber-400",
};

const sampleActivities: Activity[] = [
  {
    id: "1",
    type: "brain_node",
    title: "New memory created",
    description: "AI learned about your email preferences",
    timestamp: "2m ago",
    status: "success",
  },
  {
    id: "2",
    type: "agent_run",
    title: "Invoice Follow-up completed",
    description: "Sent 3 follow-up emails, recovered ₦45,000",
    timestamp: "15m ago",
    status: "success",
  },
  {
    id: "3",
    type: "brain_link",
    title: "Bidirectional link formed",
    description: "Connected TechCo Deal ↔ Q2 Revenue Goal",
    timestamp: "1h ago",
    status: "success",
  },
  {
    id: "4",
    type: "ai_conversation",
    title: "Chat with Anansi",
    description: "Discussed project timeline for Website Launch",
    timestamp: "2h ago",
  },
  {
    id: "5",
    type: "integration",
    title: "Gmail connected",
    description: "Integration is active and syncing",
    timestamp: "3h ago",
    status: "success",
  },
];

interface ActivityFeedProps {
  className?: string;
  limit?: number;
}

/**
 * Recent Activity feed for the dashboard.
 * Shows the latest agent runs, conversations, brain changes, and integration updates.
 */
export function ActivityFeed({ className, limit = 5 }: ActivityFeedProps) {
  const activities = sampleActivities.slice(0, limit);

  return (
    <GlassCard variant="base" padding="md" className={className}>
      <GlassCardHeader>
        <GlassCardTitle>Recent Activity</GlassCardTitle>
      </GlassCardHeader>
      <div className="space-y-1">
        {activities.map((activity) => (
          <div
            key={activity.id}
            className={cn(
              "flex items-start gap-3 px-3 py-2.5 rounded-lg",
              "transition-colors hover:bg-white/5",
            )}
          >
            {/* Icon */}
            <span
              className={cn(
                "shrink-0 mt-0.5",
                activityColors[activity.type],
              )}
            >
              {activityIcons[activity.type]}
            </span>

            {/* Content */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                {activity.title}
              </p>
              <p className="text-xs text-[var(--color-text-muted)] mt-0.5 line-clamp-1">
                {activity.description}
              </p>
            </div>

            {/* Time + Status */}
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-xs text-[var(--color-text-disabled)]">
                {activity.timestamp}
              </span>
              {activity.status === "success" && (
                <span className="h-2 w-2 rounded-full bg-semantic-success-light" />
              )}
              {activity.status === "error" && (
                <span className="h-2 w-2 rounded-full bg-semantic-error-light" />
              )}
            </div>
          </div>
        ))}
      </div>
    </GlassCard>
  );
}
