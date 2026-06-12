/**
 * BlockConfigPanel — Dynamic right-side panel for configuring the selected block.
 *
 * Renders different form fields based on block type/subtype.
 * Supports AI blocks, Action blocks, Logic blocks, and Trigger blocks.
 */

"use client";

import { useCallback, useMemo, useState } from "react";
import {
  X,
  Copy,
  Trash2,
  Beaker,
  Save,
  ChevronDown,
  ChevronUp,
  Play,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useWorkshopStore, type WorkshopNode } from "@/stores/workshop";
import { GlassCard } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Input } from "@/components/ui/Input";

// ─── Props ──────────────────────────────────────────────────────────────────────

interface BlockConfigPanelProps {
  className?: string;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function BlockConfigPanel({ className }: BlockConfigPanelProps) {
  const {
    nodes,
    selectedNodeId,
    updateNodeConfig,
    removeNode,
    selectNode,
    addNode,
  } = useWorkshopStore();

  const selectedNode = useMemo(
    () => nodes.find((n) => n.id === selectedNodeId) || null,
    [nodes, selectedNodeId]
  );

  const handleClose = useCallback(() => {
    selectNode(null);
  }, [selectNode]);

  const handleDelete = useCallback(() => {
    if (selectedNode) {
      removeNode(selectedNode.id);
    }
  }, [selectedNode, removeNode]);

  const handleDuplicate = useCallback(() => {
    if (selectedNode) {
      const pos = {
        x: selectedNode.position.x + 50,
        y: selectedNode.position.y + 50,
      };
      addNode(selectedNode.data.type, selectedNode.data.subtype, pos, selectedNode.data.config);
    }
  }, [selectedNode, addNode]);

  const handleConfigChange = useCallback(
    (field: string, value: unknown) => {
      if (selectedNode) {
        updateNodeConfig(selectedNode.id, { [field]: value });
      }
    },
    [selectedNode, updateNodeConfig]
  );

  const handleTestBlock = useCallback(async () => {
    if (!selectedNode) return;
    // In a real implementation, this would call the API to test just this block
    console.log("Testing block:", selectedNode.data.subtype, selectedNode.data.config);
  }, [selectedNode]);

  if (!selectedNode) {
    return (
      <div className={cn("flex flex-col h-full", className)}>
        <div className="px-4 py-3 border-b border-[var(--color-border-subtle)]">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)]">
            Block Configuration
          </h3>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center px-6">
            <div className="w-10 h-10 rounded-xl bg-[var(--color-surface-elevated)] flex items-center justify-center mx-auto mb-3">
              <Beaker className="h-5 w-5 text-[var(--color-text-muted)]" />
            </div>
            <p className="text-sm text-[var(--color-text-muted)]">
              Select a block on the canvas to configure it
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-subtle)]">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-[var(--color-text-primary)] truncate">
            {selectedNode.data.label}
          </h3>
          <p className="text-[11px] text-[var(--color-text-muted)] capitalize">
            {selectedNode.data.type} · {selectedNode.data.subtype}
          </p>
        </div>
        <button
          onClick={handleClose}
          className="p-1 rounded hover:bg-white/5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Config Form */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-5">
        <ConfigForm
          type={selectedNode.data.type}
          subtype={selectedNode.data.subtype}
          config={selectedNode.data.config}
          onChange={handleConfigChange}
        />
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-[var(--color-border-subtle)] space-y-2">
        <AnansiButton
          variant="secondary"
          size="sm"
          icon={<Play className="h-3.5 w-3.5" />}
          fullWidth
          onClick={handleTestBlock}
        >
          Test This Block
        </AnansiButton>

        <div className="flex gap-2">
          <button
            onClick={handleDuplicate}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:border-[var(--color-border-subtle)]/80 transition-colors"
          >
            <Copy className="h-3.5 w-3.5" />
            Duplicate
          </button>
          <button
            onClick={handleDelete}
            className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border border-semantic-error/20 text-semantic-error hover:bg-semantic-error/10 transition-colors"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Dynamic Config Form ────────────────────────────────────────────────────────

interface ConfigFormProps {
  type: string;
  subtype: string;
  config: Record<string, unknown>;
  onChange: (field: string, value: unknown) => void;
}

function ConfigForm({ type, subtype, config, onChange }: ConfigFormProps) {
  if (type === "trigger") return <TriggerConfig subtype={subtype} config={config} onChange={onChange} />;
  if (type === "ai") return <AIConfig subtype={subtype} config={config} onChange={onChange} />;
  if (type === "action") return <ActionConfig subtype={subtype} config={config} onChange={onChange} />;
  if (type === "logic") return <LogicConfig subtype={subtype} config={config} onChange={onChange} />;
  if (type === "connector") return <ConnectorConfig config={config} onChange={onChange} />;

  return <p className="text-xs text-[var(--color-text-muted)]">No configuration available</p>;
}

// ── Trigger Config ──────────────────────────────────────────────────────────────

function TriggerConfig({ subtype, config, onChange }: ConfigFormProps) {
  switch (subtype) {
    case "schedule":
      return (
        <>
          <FieldGroup label="Schedule">
            <Input
              label="Cron Expression"
              value={(config.cron as string) || ""}
              onChange={(e) => onChange("cron", e.target.value)}
              placeholder="0 9 * * 1-5"
              helperText="Min Hour Day Month Weekday"
            />
            <Input
              label="Timezone"
              value={(config.timezone as string) || "UTC"}
              onChange={(e) => onChange("timezone", e.target.value)}
              placeholder="UTC"
            />
            <Input
              label="Label"
              value={(config.label as string) || ""}
              onChange={(e) => onChange("label", e.target.value)}
              placeholder="Daily morning briefing"
            />
          </FieldGroup>
          <CronHelper cron={config.cron as string} />
        </>
      );
    case "webhook":
      return (
        <FieldGroup label="Webhook Configuration">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Method</label>
            <select
              value={(config.method as string) || "POST"}
              onChange={(e) => onChange("method", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="POST">POST</option>
              <option value="GET">GET</option>
              <option value="PUT">PUT</option>
              <option value="PATCH">PATCH</option>
            </select>
          </div>
          <Input
            label="Verification Secret"
            value={(config.secret as string) || ""}
            onChange={(e) => onChange("secret", e.target.value)}
            placeholder="Optional HMAC secret"
            type="password"
          />
        </FieldGroup>
      );
    case "email_received":
      return (
        <FieldGroup label="Email Filters">
          <Input
            label="From Filter"
            value={(config.from_filter as string) || ""}
            onChange={(e) => onChange("from_filter", e.target.value)}
            placeholder="@company.com"
          />
          <Input
            label="Subject Contains"
            value={(config.subject_filter as string) || ""}
            onChange={(e) => onChange("subject_filter", e.target.value)}
          />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(config.has_attachments as boolean) || false}
              onChange={(e) => onChange("has_attachments", e.target.checked)}
              className="rounded border-[var(--color-border-subtle)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">Has Attachments</span>
          </label>
        </FieldGroup>
      );
    case "message_received":
      return (
        <FieldGroup label="Message Filters">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Channel</label>
            <select
              value={(config.channel as string) || "any"}
              onChange={(e) => onChange("channel", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="any">Any</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="slack">Slack</option>
              <option value="telegram">Telegram</option>
              <option value="discord">Discord</option>
            </select>
          </div>
          <Input
            label="Keyword Filter"
            value={(config.keyword_filter as string) || ""}
            onChange={(e) => onChange("keyword_filter", e.target.value)}
          />
        </FieldGroup>
      );
    default:
      return <p className="text-xs text-[var(--color-text-muted)]">Trigger configuration</p>;
  }
}

// ── AI Config ──────────────────────────────────────────────────────────────────

function AIConfig({ subtype, config, onChange }: ConfigFormProps) {
  const ModelSelect = () => (
    <div className="space-y-2">
      <label className="text-xs font-medium text-[var(--color-text-secondary)]">Model</label>
      <select
        value={(config.model as string) || "claude-sonnet-4"}
        onChange={(e) => onChange("model", e.target.value)}
        className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
      >
        <option value="claude-sonnet-4">Claude Sonnet 4</option>
        <option value="claude-haiku-3">Claude Haiku 3</option>
        <option value="gpt-4o">GPT-4o</option>
        <option value="gpt-4o-mini">GPT-4o Mini</option>
        <option value="llama3">Llama 3</option>
      </select>
    </div>
  );

  switch (subtype) {
    case "conversation":
      return (
        <FieldGroup label="AI Conversation">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">System Prompt</label>
            <textarea
              value={(config.system_prompt as string) || ""}
              onChange={(e) => onChange("system_prompt", e.target.value)}
              rows={6}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40 font-mono"
              placeholder="You are a helpful assistant..."
            />
          </div>
          <ModelSelect />
          <Input
            label="Temperature"
            type="number"
            min={0}
            max={2}
            step={0.1}
            value={(config.temperature as number) ?? 0.7}
            onChange={(e) => onChange("temperature", parseFloat(e.target.value))}
          />
          <Input
            label="Max Tokens"
            type="number"
            min={1}
            max={128000}
            value={(config.max_tokens as number) ?? 4096}
            onChange={(e) => onChange("max_tokens", parseInt(e.target.value))}
          />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(config.memory_context as boolean) || false}
              onChange={(e) => onChange("memory_context", e.target.checked)}
              className="rounded border-[var(--color-border-subtle)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">Include memory context</span>
          </label>
        </FieldGroup>
      );
    case "extract":
      return (
        <FieldGroup label="AI Extract">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Extraction Prompt</label>
            <textarea
              value={(config.prompt as string) || ""}
              onChange={(e) => onChange("prompt", e.target.value)}
              rows={4}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <ModelSelect />
        </FieldGroup>
      );
    case "classify":
      return (
        <FieldGroup label="AI Classify">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Classification Prompt</label>
            <textarea
              value={(config.prompt as string) || ""}
              onChange={(e) => onChange("prompt", e.target.value)}
              rows={3}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <ModelSelect />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(config.multi_label as boolean) || false}
              onChange={(e) => onChange("multi_label", e.target.checked)}
              className="rounded border-[var(--color-border-subtle)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">Allow multiple categories</span>
          </label>
        </FieldGroup>
      );
    case "summarize":
      return (
        <FieldGroup label="AI Summarize">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Length</label>
            <select
              value={(config.length as string) || "medium"}
              onChange={(e) => onChange("length", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="short">Short</option>
              <option value="medium">Medium</option>
              <option value="long">Long</option>
              <option value="bullet_points">Bullet Points</option>
            </select>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Style</label>
            <select
              value={(config.style as string) || "concise"}
              onChange={(e) => onChange("style", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="concise">Concise</option>
              <option value="detailed">Detailed</option>
              <option value="executive">Executive</option>
              <option value="simple">Simple</option>
            </select>
          </div>
          <Input
            label="Focus Area"
            value={(config.focus as string) || ""}
            onChange={(e) => onChange("focus", e.target.value)}
            placeholder="key decisions, action items"
          />
          <ModelSelect />
        </FieldGroup>
      );
    case "generate":
      return (
        <FieldGroup label="AI Generate">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Generation Prompt</label>
            <textarea
              value={(config.prompt as string) || ""}
              onChange={(e) => onChange("prompt", e.target.value)}
              rows={6}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Output Format</label>
            <select
              value={(config.format as string) || "text"}
              onChange={(e) => onChange("format", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="text">Text</option>
              <option value="json">JSON</option>
              <option value="markdown">Markdown</option>
              <option value="html">HTML</option>
              <option value="code">Code</option>
            </select>
          </div>
          <ModelSelect />
        </FieldGroup>
      );
    case "transform":
      return (
        <FieldGroup label="AI Transform">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Transformation</label>
            <textarea
              value={(config.transformation as string) || ""}
              onChange={(e) => onChange("transformation", e.target.value)}
              rows={3}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
              placeholder="Translate to French"
            />
          </div>
          <Input
            label="Input Field (JSON path)"
            value={(config.input_field as string) || ""}
            onChange={(e) => onChange("input_field", e.target.value)}
            placeholder="content.body"
          />
          <ModelSelect />
        </FieldGroup>
      );
    default:
      return <p className="text-xs text-[var(--color-text-muted)]">AI block configuration</p>;
  }
}

// ── Action Config ──────────────────────────────────────────────────────────────

function ActionConfig({ subtype, config, onChange }: ConfigFormProps) {
  switch (subtype) {
    case "send_email":
      return (
        <FieldGroup label="Send Email">
          <Input
            label="To"
            value={(config.to as string) || ""}
            onChange={(e) => onChange("to", e.target.value)}
            placeholder="recipient@example.com"
          />
          <Input
            label="Subject"
            value={(config.subject as string) || ""}
            onChange={(e) => onChange("subject", e.target.value)}
          />
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Body</label>
            <textarea
              value={(config.body as string) || ""}
              onChange={(e) => onChange("body", e.target.value)}
              rows={6}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <Input label="CC" value={(config.cc as string) || ""} onChange={(e) => onChange("cc", e.target.value)} />
          <Input label="BCC" value={(config.bcc as string) || ""} onChange={(e) => onChange("bcc", e.target.value)} />
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={(config.draft_only as boolean) || false}
              onChange={(e) => onChange("draft_only", e.target.checked)}
              className="rounded border-[var(--color-border-subtle)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">Save as draft only</span>
          </label>
        </FieldGroup>
      );
    case "send_whatsapp":
      return (
        <FieldGroup label="Send WhatsApp">
          <Input
            label="Recipient"
            value={(config.to as string) || ""}
            onChange={(e) => onChange("to", e.target.value)}
            placeholder="+2348012345678"
          />
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Message</label>
            <textarea
              value={(config.message as string) || ""}
              onChange={(e) => onChange("message", e.target.value)}
              rows={4}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
          <Input
            label="Media URL"
            value={(config.media_url as string) || ""}
            onChange={(e) => onChange("media_url", e.target.value)}
            placeholder="https://..."
          />
        </FieldGroup>
      );
    case "http_request":
      return (
        <FieldGroup label="HTTP Request">
          <Input
            label="URL"
            value={(config.url as string) || ""}
            onChange={(e) => onChange("url", e.target.value)}
            placeholder="https://api.example.com/data"
          />
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Method</label>
            <select
              value={(config.method as string) || "GET"}
              onChange={(e) => onChange("method", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="PATCH">PATCH</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
          <Input
            label="Timeout (seconds)"
            type="number"
            min={1}
            max={300}
            value={(config.timeout_seconds as number) ?? 30}
            onChange={(e) => onChange("timeout_seconds", parseInt(e.target.value))}
          />
        </FieldGroup>
      );
    case "post_slack":
      return (
        <FieldGroup label="Post to Slack">
          <Input
            label="Channel"
            value={(config.channel as string) || ""}
            onChange={(e) => onChange("channel", e.target.value)}
            placeholder="#general"
          />
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Message</label>
            <textarea
              value={(config.message as string) || ""}
              onChange={(e) => onChange("message", e.target.value)}
              rows={4}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40"
            />
          </div>
        </FieldGroup>
      );
    default:
      return <p className="text-xs text-[var(--color-text-muted)]">Action configuration</p>;
  }
}

// ── Logic Config ───────────────────────────────────────────────────────────────

function LogicConfig({ subtype, config, onChange }: ConfigFormProps) {
  switch (subtype) {
    case "condition":
      return (
        <FieldGroup label="Condition">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">
              Expression (use <code className="text-amber-400">data</code> variable)
            </label>
            <textarea
              value={(config.expression as string) || ""}
              onChange={(e) => onChange("expression", e.target.value)}
              rows={2}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40 font-mono"
              placeholder="data.score > 50"
            />
            <p className="text-[10px] text-[var(--color-text-muted)]">
              Example: <code className="text-amber-400/80">data.score &gt; 50</code> or{" "}
              <code className="text-amber-400/80">data.status == "active"</code>
            </p>
          </div>
          <Input
            label="True Label"
            value={(config.label_true as string) || "True"}
            onChange={(e) => onChange("label_true", e.target.value)}
          />
          <Input
            label="False Label"
            value={(config.label_false as string) || "False"}
            onChange={(e) => onChange("label_false", e.target.value)}
          />
        </FieldGroup>
      );
    case "delay":
      return (
        <FieldGroup label="Delay">
          <Input
            label="Duration"
            type="number"
            min={0}
            value={(config.duration as number) ?? 5}
            onChange={(e) => onChange("duration", parseInt(e.target.value))}
          />
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">Unit</label>
            <select
              value={(config.unit as string) || "seconds"}
              onChange={(e) => onChange("unit", e.target.value)}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)]"
            >
              <option value="seconds">Seconds</option>
              <option value="minutes">Minutes</option>
              <option value="hours">Hours</option>
            </select>
          </div>
        </FieldGroup>
      );
    case "router":
      return (
        <FieldGroup label="Router">
          <Input
            label="Default Case Label"
            value={(config.default_case as string) || "Other"}
            onChange={(e) => onChange("default_case", e.target.value)}
          />
          <p className="text-xs text-[var(--color-text-muted)]">
            Configure cases by editing the agent definition directly.
          </p>
        </FieldGroup>
      );
    case "loop":
      return (
        <FieldGroup label="Loop">
          <Input
            label="Max Iterations"
            type="number"
            min={0}
            max={1000}
            value={(config.iterations as number) ?? 10}
            onChange={(e) => onChange("iterations", parseInt(e.target.value))}
          />
          <Input
            label="Batch Size"
            type="number"
            min={1}
            max={50}
            value={(config.batch_size as number) ?? 1}
            onChange={(e) => onChange("batch_size", parseInt(e.target.value))}
          />
          <Input
            label="Input Array Field (JSON path)"
            value={(config.input_array_field as string) || ""}
            onChange={(e) => onChange("input_array_field", e.target.value)}
            placeholder="data.items"
          />
        </FieldGroup>
      );
    case "filter":
      return (
        <FieldGroup label="Filter">
          <div className="space-y-2">
            <label className="text-xs font-medium text-[var(--color-text-secondary)]">
              Condition (<code className="text-amber-400">item</code> variable)
            </label>
            <textarea
              value={(config.condition as string) || ""}
              onChange={(e) => onChange("condition", e.target.value)}
              rows={2}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] resize-y focus:outline-none focus:border-amber-500/40 font-mono"
              placeholder="item.active == True"
            />
          </div>
          <Input
            label="Input Array Field"
            value={(config.input_array_field as string) || ""}
            onChange={(e) => onChange("input_array_field", e.target.value)}
          />
        </FieldGroup>
      );
    default:
      return <p className="text-xs text-[var(--color-text-muted)]">Logic configuration</p>;
  }
}

// ── Connector Config ───────────────────────────────────────────────────────────

function ConnectorConfig({ config, onChange }: ConfigFormProps) {
  return (
    <FieldGroup label="Connector">
      <p className="text-xs text-[var(--color-text-muted)]">
        Connector blocks are dynamically generated from your connected integrations.
        Connect a service in the Integrations page to use its actions here.
      </p>
    </FieldGroup>
  );
}

// ─── FieldGroup ─────────────────────────────────────────────────────────────────

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-semibold text-[var(--color-text-primary)] uppercase tracking-wider">
        {label}
      </h4>
      {children}
    </div>
  );
}

// ─── CronHelper ─────────────────────────────────────────────────────────────────

function CronHelper({ cron }: { cron: string }) {
  if (!cron) return null;

  const descriptions: Record<string, string> = {
    "0 9 * * 1-5": "Weekdays at 9:00 AM",
    "0 9 * * *": "Every day at 9:00 AM",
    "*/15 * * * *": "Every 15 minutes",
    "0 */2 * * *": "Every 2 hours",
    "0 0 * * 0": "Every Sunday at midnight",
    "0 0 1 * *": "First day of every month",
  };

  const desc = descriptions[cron];
  if (!desc) return null;

  return (
    <div className="rounded-lg px-3 py-2 bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)]">
      <p className="text-[11px] text-[var(--color-text-muted)]">
        <span className="text-amber-400/80 font-medium">Preview:</span> {desc}
      </p>
    </div>
  );
}
