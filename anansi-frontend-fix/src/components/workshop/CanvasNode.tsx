/**
 * CanvasNode — Custom React Flow node types for the agent workshop.
 *
 * 5 node types: triggerNode, aiNode, actionNode, logicNode, connectorNode
 * Each has distinct visuals, status indicators, ports, and config previews.
 */

"use client";

import { memo, useCallback } from "react";
import { Handle, Position, useNodeId, useReactFlow, type NodeProps } from "reactflow";
import {
  Clock,
  Webhook,
  Mail,
  MessageSquare,
  File,
  ClipboardList,
  Zap,
  Brain,
  FileSearch,
  Tags,
  FileText,
  Sparkles,
  Shuffle,
  Send,
  MessageCircle,
  UserPlus,
  Table,
  Globe,
  FilePlus,
  Slack,
  GitBranch,
  Filter,
  GitFork,
  Hourglass,
  Repeat2,
  Pause,
  Plug,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { cn } from "../../lib/utils";
import type { WorkshopNodeData } from "../../stores/workshop";

// ─── Icon Map ───────────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, React.ReactNode> = {
  schedule: <Clock className="h-4 w-4" />,
  webhook: <Webhook className="h-4 w-4" />,
  email_received: <Mail className="h-4 w-4" />,
  message_received: <MessageSquare className="h-4 w-4" />,
  file_changed: <File className="h-4 w-4" />,
  form_submitted: <ClipboardList className="h-4 w-4" />,
  event: <Zap className="h-4 w-4" />,
  conversation: <Brain className="h-4 w-4" />,
  extract: <FileSearch className="h-4 w-4" />,
  classify: <Tags className="h-4 w-4" />,
  summarize: <FileText className="h-4 w-4" />,
  generate: <Sparkles className="h-4 w-4" />,
  transform: <Shuffle className="h-4 w-4" />,
  send_email: <Send className="h-4 w-4" />,
  send_whatsapp: <MessageCircle className="h-4 w-4" />,
  create_crm_record: <UserPlus className="h-4 w-4" />,
  update_sheet: <Table className="h-4 w-4" />,
  http_request: <Globe className="h-4 w-4" />,
  create_file: <FilePlus className="h-4 w-4" />,
  post_slack: <Slack className="h-4 w-4" />,
  condition: <GitBranch className="h-4 w-4" />,
  filter: <Filter className="h-4 w-4" />,
  router: <GitFork className="h-4 w-4" />,
  delay: <Hourglass className="h-4 w-4" />,
  loop: <Repeat2 className="h-4 w-4" />,
  wait: <Pause className="h-4 w-4" />,
  custom: <Plug className="h-4 w-4" />,
};

// ─── Node Type Config ───────────────────────────────────────────────────────────

interface NodeTypeConfig {
  borderColor: string;
  bgColor: string;
  accentColor: string;
  labelColor: string;
  shape: "rounded" | "pill" | "hexagonal" | "diamond" | "rectangle";
}

const NODE_TYPE_CONFIGS: Record<string, NodeTypeConfig> = {
  triggerNode: {
    borderColor: "#22C55E",
    bgColor: "rgba(34, 197, 94, 0.08)",
    accentColor: "#22C55E",
    labelColor: "#22C55E",
    shape: "rounded",
  },
  aiNode: {
    borderColor: "#8B5CF6",
    bgColor: "rgba(139, 92, 246, 0.08)",
    accentColor: "#8B5CF6",
    labelColor: "#8B5CF6",
    shape: "pill",
  },
  actionNode: {
    borderColor: "#F59E0B",
    bgColor: "rgba(245, 158, 11, 0.08)",
    accentColor: "#F59E0B",
    labelColor: "#F59E0B",
    shape: "rounded",
  },
  logicNode: {
    borderColor: "#14B8A6",
    bgColor: "rgba(20, 184, 166, 0.08)",
    accentColor: "#14B8A6",
    labelColor: "#14B8A6",
    shape: "diamond",
  },
  connectorNode: {
    borderColor: "#3B82F6",
    bgColor: "rgba(59, 130, 246, 0.08)",
    accentColor: "#3B82F6",
    labelColor: "#3B82F6",
    shape: "rectangle",
  },
};

// ─── Status Indicator ───────────────────────────────────────────────────────────

function StatusIndicator({ status }: { status: string }) {
  if (status === "running") {
    return (
      <div className="absolute -top-1 -right-1 w-3 h-3">
        <span className="absolute inset-0 rounded-full bg-amber-400 animate-ping opacity-75" />
        <span className="absolute inset-0 rounded-full bg-amber-400 flex items-center justify-center">
          <Loader2 className="h-2 w-2 text-white animate-spin" />
        </span>
      </div>
    );
  }
  if (status === "success") {
    return (
      <div className="absolute -top-1 -right-1">
        <CheckCircle2 className="h-3 w-3 text-semantic-success" />
      </div>
    );
  }
  if (status === "error") {
    return (
      <div className="absolute -top-1 -right-1">
        <AlertCircle className="h-3 w-3 text-semantic-error" />
      </div>
    );
  }
  return null;
}

// ─── Config Preview ─────────────────────────────────────────────────────────────

function ConfigPreview({ data }: { data: WorkshopNodeData }) {
  const config = data.config;
  const entries: string[] = [];

  if (data.subtype === "schedule") {
    entries.push(config.cron as string);
  } else if (data.subtype === "webhook") {
    entries.push(`Method: ${config.method}`);
  } else if (["conversation", "generate", "extract"].includes(data.subtype)) {
    const prompt = (config.system_prompt || config.prompt || "") as string;
    entries.push(prompt.slice(0, 50) + (prompt.length > 50 ? "..." : ""));
  } else if (data.subtype === "condition") {
    entries.push(config.expression as string);
  } else if (data.subtype === "send_email") {
    entries.push(`To: ${config.to || "..."}`);
    entries.push(`Subject: ${(config.subject || "").slice(0, 30)}`);
  } else if (data.subtype === "send_whatsapp") {
    entries.push(`To: ${config.to || "..."}`);
  } else if (data.subtype === "http_request") {
    entries.push(`${config.method} ${(config.url || "").slice(0, 30)}`);
  } else if (data.subtype === "delay") {
    entries.push(`${config.duration} ${config.unit}`);
  } else if (data.subtype === "classify") {
    const cats = config.categories as Array<{ name: string }> | undefined;
    entries.push(`${cats?.length || 0} categories`);
  }

  if (entries.length === 0) return null;

  return (
    <div className="mt-2 pt-2 border-t border-[var(--color-border-subtle)]/50">
      {entries.map((entry, i) => (
        <div
          key={i}
          className="text-[10px] text-[var(--color-text-muted)] truncate font-mono leading-relaxed"
        >
          {entry}
        </div>
      ))}
    </div>
  );
}

// ─── Base Node Component ────────────────────────────────────────────────────────

const BaseNode = memo(function BaseNode({
  data,
  selected,
  type,
}: NodeProps<WorkshopNodeData> & { type: string }) {
  const config = NODE_TYPE_CONFIGS[type] || NODE_TYPE_CONFIGS.actionNode;

  // Selection glow
  const selectedStyles = selected
    ? {
        boxShadow: `0 0 0 2px ${config.accentColor}, 0 0 20px ${config.accentColor}40`,
      }
    : {};

  // Error/Running glow
  const glowStyle = data.status === "error"
    ? { boxShadow: "0 0 12px rgba(220, 38, 38, 0.5)" }
    : data.status === "running"
    ? { boxShadow: "0 0 12px rgba(245, 158, 11, 0.4)" }
    : {};

  const icon = ICON_MAP[data.subtype] || ICON_MAP.custom;

  return (
    <div
      className={cn(
        "relative min-w-[180px] max-w-[260px]",
        "backdrop-blur-xl rounded-lg border transition-all duration-200",
        selected && "z-10"
      )}
      style={{
        backgroundColor: config.bgColor,
        borderColor: selected ? config.accentColor : `${config.borderColor}40`,
        ...selectedStyles,
        ...glowStyle,
        borderRadius: config.shape === "pill" ? "9999px" :
                     config.shape === "diamond" ? "8px" :
                     config.shape === "hexagonal" ? "12px" : "10px",
      }}
    >
      {/* Status indicator */}
      <StatusIndicator status={data.status} />

      {/* Error tooltip */}
      {data.status === "error" && data.errorMessage && (
        <div className="absolute -bottom-8 left-0 right-0 z-20">
          <div className="px-2 py-1 rounded text-[10px] bg-semantic-error/90 text-white truncate shadow-lg">
            {data.errorMessage}
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2">
        {/* Icon */}
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
          style={{ backgroundColor: `${config.accentColor}18` }}
        >
          <span style={{ color: config.accentColor }}>{icon}</span>
        </div>

        {/* Label */}
        <div className="min-w-0 flex-1">
          <div
            className="text-xs font-semibold truncate"
            style={{ color: config.labelColor }}
          >
            {data.label}
          </div>
          <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider">
            {data.type}
          </div>
        </div>
      </div>

      {/* Config preview */}
      <div className="px-3 pb-2">
        <ConfigPreview data={data} />
      </div>

      {/* Input handle (left) */}
      <Handle
        type="target"
        position={Position.Left}
        className="!w-3 !h-3 !border-2 !bg-[var(--color-bg-deepest)] !border-current"
        style={{ borderColor: config.accentColor }}
      />

      {/* Output handle (right) */}
      <Handle
        type="source"
        position={Position.Right}
        className="!w-3 !h-3 !border-2 !bg-[var(--color-bg-deepest)] !border-current"
        style={{ borderColor: config.accentColor }}
      />
    </div>
  );
});

// ─── Export Node Types ──────────────────────────────────────────────────────────

export const TriggerNode = memo(function TriggerNode(props: NodeProps<WorkshopNodeData>) {
  return <BaseNode {...props} type="triggerNode" />;
});

export const AiNode = memo(function AiNode(props: NodeProps<WorkshopNodeData>) {
  return <BaseNode {...props} type="aiNode" />;
});

export const ActionNode = memo(function ActionNode(props: NodeProps<WorkshopNodeData>) {
  return <BaseNode {...props} type="actionNode" />;
});

export const LogicNode = memo(function LogicNode(props: NodeProps<WorkshopNodeData>) {
  return <BaseNode {...props} type="logicNode" />;
});

export const ConnectorNode = memo(function ConnectorNode(props: NodeProps<WorkshopNodeData>) {
  return <BaseNode {...props} type="connectorNode" />;
});
