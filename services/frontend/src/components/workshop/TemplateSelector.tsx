/**
 * TemplateSelector — Grid of agent templates for new agent creation.
 *
 * Shows blank canvas + pre-built templates with descriptions,
 * block counts, and estimated memory impact.
 */

"use client";

import { useState } from "react";
import {
  FilePlus,
  Mail,
  Target,
  Sun,
  Receipt,
  Share2,
  Sparkles,
  Layers,
  MemoryStick as Memory,
  TrendingUp,
} from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import type { AgentDefinition } from "@/types";

// ─── Template Definitions ───────────────────────────────────────────────────────

export interface AgentTemplate {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  popularity: "hot" | "popular" | "new" | "";
  blockCount: number;
  estimatedMemoryNodes: number;
  estimatedMemoryLinks: number;
  color: string;
  definition: AgentDefinition;
}

export const AGENT_TEMPLATES: AgentTemplate[] = [
  {
    id: "blank",
    name: "Blank Canvas",
    description: "Start from scratch with an empty agent. Add your own blocks and configure everything yourself.",
    icon: <FilePlus className="h-6 w-6" />,
    popularity: "",
    blockCount: 0,
    estimatedMemoryNodes: 0,
    estimatedMemoryLinks: 0,
    color: "#A8A29E",
    definition: { triggers: [], blocks: [], edges: [] },
  },
  {
    id: "email-followup",
    name: "Email Follow-up",
    description: "Automatically send follow-up emails to leads or clients after a set delay. Perfect for sales outreach.",
    icon: <Mail className="h-6 w-6" />,
    popularity: "hot",
    blockCount: 4,
    estimatedMemoryNodes: 8,
    estimatedMemoryLinks: 5,
    color: "#F59E0B",
    definition: {
      triggers: [{ type: "schedule", config: { cron: "0 9 * * 1-5", timezone: "UTC" } }],
      blocks: [
        { id: "b1", type: "trigger", subtype: "schedule", config: { cron: "0 9 * * 1-5", timezone: "UTC" }, position: { x: 50, y: 200 } },
        { id: "b2", type: "ai", subtype: "conversation", config: { system_prompt: "You are a friendly sales assistant. Draft a follow-up email for a lead who hasn't responded in 3 days. Keep it warm and professional.", model: "claude-haiku-3", temperature: 0.7, max_tokens: 1024 }, position: { x: 350, y: 100 } },
        { id: "b3", type: "logic", subtype: "condition", config: { expression: "data.lead_status == 'warm'", label_true: "Warm Lead", label_false: "Cold Lead" }, position: { x: 350, y: 300 } },
        { id: "b4", type: "action", subtype: "send_email", config: { draft_only: false }, position: { x: 650, y: 200 } },
      ],
      edges: [
        { id: "e1", source: "b1", target: "b2" },
        { id: "e2", source: "b2", target: "b3" },
        { id: "e3", source: "b3", target: "b4" },
      ],
    },
  },
  {
    id: "lead-qualification",
    name: "Lead Qualification",
    description: "Score and qualify leads based on criteria. Routes hot leads to CRM and sends notifications.",
    icon: <Target className="h-6 w-6" />,
    popularity: "popular",
    blockCount: 5,
    estimatedMemoryNodes: 12,
    estimatedMemoryLinks: 8,
    color: "#8B5CF6",
    definition: {
      triggers: [{ type: "webhook", config: { method: "POST" } }],
      blocks: [
        { id: "b1", type: "trigger", subtype: "webhook", config: { method: "POST" }, position: { x: 50, y: 200 } },
        { id: "b2", type: "ai", subtype: "classify", config: { categories: [{ name: "hot", description: "High budget, decision maker, urgent timeline" }, { name: "warm", description: "Interested but not urgent" }, { name: "cold", description: "Low fit or not ready" }], multi_label: false, model: "claude-haiku-3" }, position: { x: 350, y: 100 } },
        { id: "b3", type: "ai", subtype: "extract", config: { prompt: "Extract the lead's company name, budget range, and decision maker status.", output_schema: { type: "object", properties: { company: { type: "string" }, budget: { type: "string" }, is_decision_maker: { type: "boolean" } } }, model: "claude-haiku-3" }, position: { x: 350, y: 300 } },
        { id: "b4", type: "action", subtype: "create_crm_record", config: { service: "hubspot", object_type: "contact", fields: {} }, position: { x: 650, y: 150 } },
        { id: "b5", type: "action", subtype: "send_whatsapp", config: {}, position: { x: 650, y: 350 } },
      ],
      edges: [
        { id: "e1", source: "b1", target: "b2" },
        { id: "e1b", source: "b1", target: "b3" },
        { id: "e2", source: "b2", target: "b4", label: "Hot" },
        { id: "e3", source: "b3", target: "b4" },
        { id: "e4", source: "b2", target: "b5", label: "Warm" },
      ],
    },
  },
  {
    id: "daily-briefing",
    name: "Daily Briefing",
    description: "Get a daily AI-generated summary of emails, tasks, and calendar events delivered to WhatsApp.",
    icon: <Sun className="h-6 w-6" />,
    popularity: "popular",
    blockCount: 3,
    estimatedMemoryNodes: 6,
    estimatedMemoryLinks: 3,
    color: "#14B8A6",
    definition: {
      triggers: [{ type: "schedule", config: { cron: "0 7 * * 1-5", timezone: "UTC" } }],
      blocks: [
        { id: "b1", type: "trigger", subtype: "schedule", config: { cron: "0 7 * * 1-5", timezone: "UTC" }, position: { x: 50, y: 200 } },
        { id: "b2", type: "ai", subtype: "summarize", config: { length: "short", style: "executive", model: "claude-haiku-3" }, position: { x: 350, y: 200 } },
        { id: "b3", type: "action", subtype: "send_whatsapp", config: {}, position: { x: 650, y: 200 } },
      ],
      edges: [
        { id: "e1", source: "b1", target: "b2" },
        { id: "e2", source: "b2", target: "b3" },
      ],
    },
  },
  {
    id: "invoice-reminder",
    name: "Invoice Reminder",
    description: "Send automated payment reminders for overdue invoices. Escalate after multiple reminders.",
    icon: <Receipt className="h-6 w-6" />,
    popularity: "hot",
    blockCount: 4,
    estimatedMemoryNodes: 10,
    estimatedMemoryLinks: 6,
    color: "#EF4444",
    definition: {
      triggers: [{ type: "schedule", config: { cron: "0 10 * * 1-5", timezone: "UTC" } }],
      blocks: [
        { id: "b1", type: "trigger", subtype: "schedule", config: { cron: "0 10 * * 1-5", timezone: "UTC" }, position: { x: 50, y: 200 } },
        { id: "b2", type: "ai", subtype: "generate", config: { prompt: "Generate a polite payment reminder for an overdue invoice. Include invoice number, amount, and due date.", format: "text", model: "claude-haiku-3", temperature: 0.5 }, position: { x: 350, y: 200 } },
        { id: "b3", type: "logic", subtype: "condition", config: { expression: "data.days_overdue > 30", label_true: "Escalate", label_false: "Gentle Reminder" }, position: { x: 350, y: 400 } },
        { id: "b4", type: "action", subtype: "send_email", config: { draft_only: false }, position: { x: 650, y: 200 } },
      ],
      edges: [
        { id: "e1", source: "b1", target: "b2" },
        { id: "e2", source: "b2", target: "b3" },
        { id: "e3", source: "b3", target: "b4" },
      ],
    },
  },
  {
    id: "social-media-poster",
    name: "Social Media Poster",
    description: "AI-generates and schedules social media posts across connected platforms.",
    icon: <Share2 className="h-6 w-6" />,
    popularity: "new",
    blockCount: 4,
    estimatedMemoryNodes: 9,
    estimatedMemoryLinks: 5,
    color: "#3B82F6",
    definition: {
      triggers: [{ type: "schedule", config: { cron: "0 9 * * 1,3,5", timezone: "UTC" } }],
      blocks: [
        { id: "b1", type: "trigger", subtype: "schedule", config: { cron: "0 9 * * 1,3,5", timezone: "UTC" }, position: { x: 50, y: 200 } },
        { id: "b2", type: "ai", subtype: "generate", config: { prompt: "Generate a social media post about productivity tips. Make it engaging with emojis and hashtags.", format: "text", model: "claude-haiku-3", temperature: 0.9 }, position: { x: 350, y: 200 } },
        { id: "b3", type: "action", subtype: "http_request", config: { method: "POST", timeout_seconds: 30 }, position: { x: 650, y: 100 } },
        { id: "b4", type: "logic", subtype: "delay", config: { duration: 2, unit: "hours" }, position: { x: 650, y: 350 } },
      ],
      edges: [
        { id: "e1", source: "b1", target: "b2" },
        { id: "e2", source: "b2", target: "b3" },
        { id: "e3", source: "b2", target: "b4" },
      ],
    },
  },
];

// ─── Props ──────────────────────────────────────────────────────────────────────

interface TemplateSelectorProps {
  onSelect: (template: AgentTemplate) => void;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function TemplateSelector({ onSelect }: TemplateSelectorProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-heading font-bold text-[var(--color-text-primary)]">
          Create a New Agent
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-2 max-w-lg mx-auto">
          Choose a template to start quickly, or start with a blank canvas
          and build your agent from scratch.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {AGENT_TEMPLATES.map((template) => (
          <GlassCard
            key={template.id}
            variant="interactive"
            glow={hoveredId === template.id ? "amber" : "none"}
            className={cn(
              "relative cursor-pointer transition-all duration-200",
              hoveredId === template.id && "scale-[1.02]"
            )}
            onClick={() => onSelect(template)}
            onMouseEnter={() => setHoveredId(template.id)}
            onMouseLeave={() => setHoveredId(null)}
          >
            {/* Popularity badge */}
            {template.popularity && (
              <Badge
                variant={
                  template.popularity === "hot" ? "error" :
                  template.popularity === "popular" ? "success" : "info"
                }
                size="sm"
                className="absolute top-3 right-3"
              >
                {template.popularity === "hot" && <Sparkles className="h-3 w-3" />}
                {template.popularity === "popular" && <TrendingUp className="h-3 w-3" />}
                {template.popularity === "new" && "New"}
                {template.popularity === "hot" && "Hot"}
                {template.popularity === "popular" && "Popular"}
              </Badge>
            )}

            {/* Icon */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
              style={{ backgroundColor: `${template.color}15`, color: template.color }}
            >
              {template.icon}
            </div>

            {/* Name & Description */}
            <h3 className="text-lg font-heading font-bold text-[var(--color-text-primary)] mb-1">
              {template.name}
            </h3>
            <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2 min-h-[2.5rem]">
              {template.description}
            </p>

            {/* Stats */}
            <div className="flex items-center gap-4 mt-4 pt-3 border-t border-[var(--color-border-subtle)] text-xs text-[var(--color-text-muted)]">
              <span className="flex items-center gap-1">
                <Layers className="h-3.5 w-3.5" />
                {template.blockCount} blocks
              </span>
              <span className="flex items-center gap-1">
                <Memory className="h-3.5 w-3.5" />
                ~{template.estimatedMemoryNodes} mem nodes
              </span>
            </div>

            {/* Preview on hover */}
            {hoveredId === template.id && template.blockCount > 0 && (
              <div className="mt-3 pt-3 border-t border-[var(--color-border-subtle)]">
                <div className="flex flex-wrap gap-1.5">
                  {template.definition.blocks.slice(0, 5).map((block) => (
                    <span
                      key={block.id}
                      className="px-2 py-0.5 rounded text-[10px] font-medium border"
                      style={{
                        backgroundColor: `${_getBlockColor(block.type)}15`,
                        borderColor: `${_getBlockColor(block.type)}30`,
                        color: _getBlockColor(block.type),
                      }}
                    >
                      {block.subtype}
                    </span>
                  ))}
                  {template.definition.blocks.length > 5 && (
                    <span className="px-2 py-0.5 rounded text-[10px] text-[var(--color-text-muted)]">
                      +{template.definition.blocks.length - 5}
                    </span>
                  )}
                </div>
              </div>
            )}
          </GlassCard>
        ))}
      </div>
    </div>
  );
}

// ─── Helper ─────────────────────────────────────────────────────────────────────

function _getBlockColor(type: string): string {
  const colors: Record<string, string> = {
    trigger: "#22C55E",
    ai: "#8B5CF6",
    action: "#F59E0B",
    logic: "#14B8A6",
    connector: "#3B82F6",
  };
  return colors[type] || "#A8A29E";
}
