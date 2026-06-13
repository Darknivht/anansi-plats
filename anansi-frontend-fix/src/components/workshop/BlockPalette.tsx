/**
 * BlockPalette — Draggable sidebar panel with all available block types.
 *
 * Organized by category with search, drag-to-canvas support.
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import { useReactFlow } from "reactflow";
import {
  Search,
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
  ChevronDown,
  ChevronRight,
  Plug,
  Layers,
} from "lucide-react";
import { cn } from "../../lib/utils";

// ─── Block type definitions for the palette ─────────────────────────────────────

interface PaletteBlock {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ReactNode;
  color: string;
}

const BLOCK_TYPES: PaletteBlock[] = [
  // Triggers
  { id: "trigger.schedule", name: "Schedule", description: "Run on a cron schedule", category: "trigger", icon: <Clock className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.webhook", name: "Webhook", description: "Receive HTTP requests", category: "trigger", icon: <Webhook className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.email_received", name: "Email Received", description: "On incoming email", category: "trigger", icon: <Mail className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.message_received", name: "Message Received", description: "On channel message", category: "trigger", icon: <MessageSquare className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.file_changed", name: "File Changed", description: "On file create/update", category: "trigger", icon: <File className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.form_submitted", name: "Form Submitted", description: "On form submission", category: "trigger", icon: <ClipboardList className="h-4 w-4" />, color: "#22C55E" },
  { id: "trigger.event", name: "Platform Event", description: "On internal event", category: "trigger", icon: <Zap className="h-4 w-4" />, color: "#22C55E" },

  // AI
  { id: "ai.conversation", name: "AI Conversation", description: "Free-form AI chat", category: "ai", icon: <Brain className="h-4 w-4" />, color: "#8B5CF6" },
  { id: "ai.extract", name: "AI Extract", description: "Extract structured data", category: "ai", icon: <FileSearch className="h-4 w-4" />, color: "#8B5CF6" },
  { id: "ai.classify", name: "AI Classify", description: "Categorize input", category: "ai", icon: <Tags className="h-4 w-4" />, color: "#8B5CF6" },
  { id: "ai.summarize", name: "AI Summarize", description: "Summarize text", category: "ai", icon: <FileText className="h-4 w-4" />, color: "#8B5CF6" },
  { id: "ai.generate", name: "AI Generate", description: "Generate content", category: "ai", icon: <Sparkles className="h-4 w-4" />, color: "#8B5CF6" },
  { id: "ai.transform", name: "AI Transform", description: "Transform data", category: "ai", icon: <Shuffle className="h-4 w-4" />, color: "#8B5CF6" },

  // Actions
  { id: "action.send_email", name: "Send Email", description: "Send an email", category: "action", icon: <Send className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.send_whatsapp", name: "Send WhatsApp", description: "Send WhatsApp message", category: "action", icon: <MessageCircle className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.create_crm_record", name: "Create CRM Record", description: "Add to CRM", category: "action", icon: <UserPlus className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.update_sheet", name: "Update Sheet", description: "Update spreadsheet", category: "action", icon: <Table className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.http_request", name: "HTTP Request", description: "Make API call", category: "action", icon: <Globe className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.create_file", name: "Create File", description: "Save file to storage", category: "action", icon: <FilePlus className="h-4 w-4" />, color: "#F59E0B" },
  { id: "action.post_slack", name: "Post to Slack", description: "Send Slack message", category: "action", icon: <Slack className="h-4 w-4" />, color: "#F59E0B" },

  // Logic
  { id: "logic.condition", name: "Condition", description: "If/then branching", category: "logic", icon: <GitBranch className="h-4 w-4" />, color: "#14B8A6" },
  { id: "logic.filter", name: "Filter", description: "Filter array of items", category: "logic", icon: <Filter className="h-4 w-4" />, color: "#14B8A6" },
  { id: "logic.router", name: "Router", description: "Multi-case routing", category: "logic", icon: <GitFork className="h-4 w-4" />, color: "#14B8A6" },
  { id: "logic.delay", name: "Delay", description: "Pause execution", category: "logic", icon: <Hourglass className="h-4 w-4" />, color: "#14B8A6" },
  { id: "logic.loop", name: "Loop", description: "Iterate over items", category: "logic", icon: <Repeat2 className="h-4 w-4" />, color: "#14B8A6" },
  { id: "logic.wait", name: "Wait For", description: "Wait until condition", category: "logic", icon: <Pause className="h-4 w-4" />, color: "#14B8A6" },

  // Connector (placeholder — dynamic in integration)
  { id: "connector.custom", name: "Connector", description: "Connected service action", category: "connector", icon: <Plug className="h-4 w-4" />, color: "#3B82F6" },
];

const CATEGORIES = [
  { key: "trigger", label: "Triggers", icon: <Zap className="h-4 w-4" /> },
  { key: "ai", label: "AI", icon: <Brain className="h-4 w-4" /> },
  { key: "action", label: "Actions", icon: <Layers className="h-4 w-4" /> },
  { key: "logic", label: "Logic", icon: <GitBranch className="h-4 w-4" /> },
  { key: "connector", label: "Connectors", icon: <Plug className="h-4 w-4" /> },
];

// ─── Drag Preview ───────────────────────────────────────────────────────────────

function BlockDragPreview({ block }: { block: PaletteBlock }) {
  return (
    <div
      className="flex items-center gap-2 px-3 py-2 rounded-lg shadow-glass-lg backdrop-blur-xl"
      style={{
        backgroundColor: `${block.color}20`,
        borderColor: `${block.color}40`,
        border: `1px solid ${block.color}40`,
      }}
    >
      <span style={{ color: block.color }}>{block.icon}</span>
      <span className="text-sm font-medium text-[var(--color-text-primary)] whitespace-nowrap">
        {block.name}
      </span>
    </div>
  );
}

// ─── Palette Item ───────────────────────────────────────────────────────────────

function PaletteItem({ block }: { block: PaletteBlock }) {
  const [category, subtype] = block.id.split(".");

  const handleDragStart = useCallback(
    (e: React.DragEvent) => {
      e.dataTransfer.setData("application/reactflow", JSON.stringify({ type: category, subtype }));
      e.dataTransfer.effectAllowed = "move";
    },
    [category, subtype],
  );

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-grab active:cursor-grabbing",
        "transition-all duration-150 ease-anansi",
        "hover:bg-white/5 border border-transparent hover:border-[var(--color-border-subtle)]",
        "group"
      )}
      title={block.description}
    >
      {/* Color indicator */}
      <div
        className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
        style={{ backgroundColor: `${block.color}18` }}
      >
        <span className="text-[11px]" style={{ color: block.color }}>
          {block.icon}
        </span>
      </div>

      {/* Name + Description */}
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-[var(--color-text-primary)] truncate">
          {block.name}
        </div>
        <div className="text-[11px] text-[var(--color-text-muted)] truncate">
          {block.description}
        </div>
      </div>
    </div>
  );
}

// ─── Category Section ───────────────────────────────────────────────────────────

function CategorySection({
  category,
  blocks,
  defaultOpen,
}: {
  category: (typeof CATEGORIES)[0];
  blocks: PaletteBlock[];
  defaultOpen: boolean;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const cat = CATEGORIES.find((c) => c.key === category.key)!;

  if (blocks.length === 0) return null;

  return (
    <div className="mb-1">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 w-full px-3 py-2 text-xs font-semibold uppercase tracking-wider text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)] transition-colors"
      >
        {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
        <span>{cat.icon}</span>
        <span>{cat.label}</span>
        <span className="ml-auto text-[10px] opacity-50">{blocks.length}</span>
      </button>

      {isOpen && (
        <div className="space-y-0.5 px-1">
          {blocks.map((block) => (
            <PaletteItem key={block.id} block={block} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────────

interface BlockPaletteProps {
  className?: string;
}

export function BlockPalette({ className }: BlockPaletteProps) {
  const [search, setSearch] = useState("");

  const filteredBlocks = useMemo(() => {
    if (!search.trim()) return BLOCK_TYPES;
    const q = search.toLowerCase();
    return BLOCK_TYPES.filter(
      (b) =>
        b.name.toLowerCase().includes(q) ||
        b.description.toLowerCase().includes(q) ||
        b.category.toLowerCase().includes(q)
    );
  }, [search]);

  const groupedBlocks = useMemo(() => {
    const groups: Record<string, PaletteBlock[]> = {};
    for (const block of filteredBlocks) {
      if (!groups[block.category]) groups[block.category] = [];
      groups[block.category].push(block);
    }
    return groups;
  }, [filteredBlocks]);

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
          Block Palette
        </h3>
        <p className="text-[11px] text-[var(--color-text-muted)] mt-0.5">
          Drag blocks to the canvas
        </p>
      </div>

      {/* Search */}
      <div className="px-3 py-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[var(--color-text-muted)]" />
          <input
            type="text"
            placeholder="Search blocks..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={cn(
              "w-full rounded-md pl-8 pr-3 py-1.5 text-xs",
              "bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)]",
              "text-[var(--color-text-primary)] placeholder:text-[var(--color-text-disabled)]",
              "focus:outline-none focus:border-amber-500/40"
            )}
          />
        </div>
      </div>

      {/* Block list */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1 scrollbar-thin">
        {search ? (
          // Flat view when searching
          filteredBlocks.map((block) => (
            <PaletteItem key={block.id} block={block} />
          ))
        ) : (
          // Categorized view
          CATEGORIES.map((cat) => (
            <CategorySection
              key={cat.key}
              category={cat}
              blocks={groupedBlocks[cat.key] || []}
              defaultOpen={cat.key === "trigger"}
            />
          ))
        )}

        {filteredBlocks.length === 0 && (
          <div className="text-center py-8 text-xs text-[var(--color-text-muted)]">
            No blocks match &ldquo;{search}&rdquo;
          </div>
        )}
      </div>
    </div>
  );
}

export { BLOCK_TYPES, BLOCK_TYPES as PALETTE_BLOCKS };
export type { PaletteBlock };
