/**
 * AgentTestPanel — Slide-out testing interface for agents.
 *
 * Provides sample data input, run/test execution, step-through mode,
 * and detailed results per block.
 */

"use client";

import { useCallback, useState } from "react";
import {
  Play,
  X,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
  SkipForward,
  FileText,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { AnansiButton } from "../../components/ui/AnansiButton";
import { GlassCard } from "../../components/ui/GlassCard";
import { Badge } from "../../components/ui/Badge";
import { Input } from "../../components/ui/Input";
import { useWorkshopStore, type WorkshopNode } from "../../stores/workshop";
import { api } from "../../lib/api";
import type { AgentRun } from "../../types";

// ─── Props ──────────────────────────────────────────────────────────────────────

interface AgentTestPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

// ─── Component ──────────────────────────────────────────────────────────────────

export function AgentTestPanel({ isOpen, onClose }: AgentTestPanelProps) {
  const { agentId, toAgentDefinition, nodes, setTestMode } = useWorkshopStore();
  const [sampleData, setSampleData] = useState("{\n  \n}");
  const [stepThrough, setStepThrough] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<AgentRun | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedBlocks, setExpandedBlocks] = useState<Set<string>>(new Set());
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());

  const toggleBlock = (id: string) => {
    setExpandedBlocks((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleStep = (id: string) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleRunTest = useCallback(async () => {
    setIsRunning(true);
    setError(null);
    setRunResult(null);
    setTestMode(true);
    setExpandedBlocks(new Set());
    setExpandedSteps(new Set());

    try {
      let inputData: Record<string, unknown>;
      try {
        inputData = JSON.parse(sampleData);
      } catch {
        setError("Invalid JSON in sample data");
        setIsRunning(false);
        return;
      }

      if (agentId) {
        // Run test on saved agent
        const result = await api.post<AgentRun>(`/api/v1/agents/${agentId}/test`, inputData);
        setRunResult(result);
      } else {
        // For unsaved agents, we'll simulate a test run client-side
        const definition = toAgentDefinition();
        const testResult = await simulateTestRun(definition, inputData);
        setRunResult(testResult);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Test execution failed");
    } finally {
      setIsRunning(false);
    }
  }, [agentId, sampleData, toAgentDefinition, setTestMode]);

  const handleRun = useCallback(async () => {
    if (!agentId) {
      setError("Save the agent first before running");
      return;
    }

    setIsRunning(true);
    setError(null);
    setRunResult(null);

    try {
      let inputData: Record<string, unknown>;
      try {
        inputData = JSON.parse(sampleData);
      } catch {
        setError("Invalid JSON in sample data");
        setIsRunning(false);
        return;
      }

      const result = await api.post<AgentRun>(`/api/v1/agents/${agentId}/run`, inputData);
      setRunResult(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Execution failed");
    } finally {
      setIsRunning(false);
    }
  }, [agentId, sampleData]);

  const handleClose = useCallback(() => {
    onClose();
    setRunResult(null);
    setError(null);
    setTestMode(false);
  }, [onClose, setTestMode]);

  if (!isOpen) return null;

  const steps = runResult?.steps || [];
  const isRunningState = runResult?.status === "running";
  const isCompleted = runResult?.status === "completed" || runResult?.status === "completed_with_errors";
  const isFailed = runResult?.status === "failed";

  return (
    <div className="fixed inset-y-0 right-0 w-[480px] max-w-[90vw] z-50 flex">
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={handleClose} />

      {/* Panel */}
      <div className="relative ml-auto w-full h-full glass-elevated flex flex-col border-l border-[var(--color-border-subtle)] animate-slide-in-right">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--color-border-subtle)]">
          <div>
            <h3 className="text-base font-heading font-bold text-[var(--color-text-primary)]">
              Agent Testing
            </h3>
            <p className="text-xs text-[var(--color-text-muted)]">
              {stepThrough ? "Step-through mode" : "Run with sample data"}
            </p>
          </div>
          <button
            onClick={handleClose}
            className="p-2 rounded-lg hover:bg-white/5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {/* Sample Data Input */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-[var(--color-text-primary)] uppercase tracking-wider">
              Sample Input Data (JSON)
            </label>
            <textarea
              value={sampleData}
              onChange={(e) => setSampleData(e.target.value)}
              rows={6}
              className="w-full rounded-lg px-3 py-2 text-sm bg-[var(--color-surface-elevated)] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] font-mono resize-y focus:outline-none focus:border-amber-500/40"
              placeholder='{"key": "value"}'
            />
          </div>

          {/* Step-through toggle */}
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={stepThrough}
              onChange={(e) => setStepThrough(e.target.checked)}
              className="rounded border-[var(--color-border-subtle)]"
            />
            <span className="text-sm text-[var(--color-text-secondary)]">
              Step-through mode (pause between blocks)
            </span>
          </label>

          {/* Error */}
          {error && (
            <div className="rounded-lg px-4 py-3 bg-semantic-error/10 border border-semantic-error/20 text-sm text-semantic-error-light">
              {error}
            </div>
          )}

          {/* Results */}
          {runResult && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-semibold text-[var(--color-text-primary)]">
                  Results
                </h4>
                <Badge
                  variant={
                    isCompleted ? "success" : isFailed ? "error" : "warning"
                  }
                  size="sm"
                >
                  {runResult.status}
                </Badge>
              </div>

              {/* Execution info */}
              <GlassCard variant="base" padding="sm">
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div>
                    <span className="text-[var(--color-text-muted)]">Duration</span>
                    <p className="font-medium text-[var(--color-text-primary)]">
                      {runResult.durationMs ? `${(runResult.durationMs / 1000).toFixed(1)}s` : "—"}
                    </p>
                  </div>
                  <div>
                    <span className="text-[var(--color-text-muted)]">Memory Nodes</span>
                    <p className="font-medium text-[var(--color-text-primary)]">
                      {runResult.memoryNodesCreated ?? 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-[var(--color-text-muted)]">Memory Links</span>
                    <p className="font-medium text-[var(--color-text-primary)]">
                      {runResult.memoryLinksCreated ?? 0}
                    </p>
                  </div>
                  <div>
                    <span className="text-[var(--color-text-muted)]">Steps</span>
                    <p className="font-medium text-[var(--color-text-primary)]">
                      {steps.length}
                    </p>
                  </div>
                </div>
              </GlassCard>

              {/* Error message */}
              {runResult.errorMessage && (
                <div className="rounded-lg px-4 py-3 bg-semantic-error/10 border border-semantic-error/20 text-sm text-semantic-error-light">
                  <span className="font-semibold">Error:</span> {runResult.errorMessage}
                </div>
              )}

              {/* Step-by-step blocks */}
              <div className="space-y-2">
                <h5 className="text-xs font-semibold text-[var(--color-text-muted)] uppercase tracking-wider">
                  Step-by-Step Execution
                </h5>

                {steps.length === 0 && (
                  <p className="text-xs text-[var(--color-text-muted)] py-4 text-center">
                    No step data available
                  </p>
                )}

                {steps.map((step: Record<string, unknown>, i: number) => {
                  const stepId = step.block_id as string || `step-${i}`;
                  const stepStatus = step.status as string;
                  const isExpanded = expandedSteps.has(stepId);
                  const duration = step.duration_ms as number;
                  const stepBlock = nodes.find((n) => n.id === stepId);

                  return (
                    <GlassCard key={stepId} variant="base" padding="sm">
                      <button
                        onClick={() => toggleStep(stepId)}
                        className="flex items-center gap-3 w-full text-left"
                      >
                        {/* Status icon */}
                        <div className="shrink-0">
                          {stepStatus === "running" && <Loader2 className="h-4 w-4 text-amber-400 animate-spin" />}
                          {stepStatus === "completed" && <CheckCircle2 className="h-4 w-4 text-semantic-success" />}
                          {stepStatus === "error" && <AlertCircle className="h-4 w-4 text-semantic-error" />}
                        </div>

                        {/* Block info */}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-[var(--color-text-primary)] truncate">
                            {stepBlock?.data?.label || step.block_subtype as string}
                          </div>
                          <div className="text-[11px] text-[var(--color-text-muted)]">
                            {step.block_type as string} · {duration ? `${(duration / 1000).toFixed(2)}s` : "—"}
                          </div>
                        </div>

                        {isExpanded ? <ChevronUp className="h-4 w-4 text-[var(--color-text-muted)]" /> : <ChevronDown className="h-4 w-4 text-[var(--color-text-muted)]" />}
                      </button>

                      {/* Expanded details */}
                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t border-[var(--color-border-subtle)] space-y-3">
                          {step.output && (
                            <div>
                              <label className="text-[10px] font-semibold text-[var(--color-text-muted)] uppercase mb-1 block">Output</label>
                              <pre className="rounded-lg px-3 py-2 bg-[var(--color-surface-elevated)] text-[11px] font-mono text-[var(--color-text-secondary)] overflow-x-auto max-h-32 overflow-y-auto">
                                {JSON.stringify(step.output, null, 2)}
                              </pre>
                            </div>
                          )}

                          {step.error && (
                            <div>
                              <label className="text-[10px] font-semibold text-semantic-error uppercase mb-1 block">Error</label>
                              <pre className="rounded-lg px-3 py-2 bg-semantic-error/10 text-[11px] font-mono text-semantic-error-light overflow-x-auto">
                                {step.error as string}
                              </pre>
                            </div>
                          )}

                          {duration && (
                            <div className="text-[11px] text-[var(--color-text-muted)]">
                              Execution time: <span className="font-medium text-[var(--color-text-secondary)]">{(duration / 1000).toFixed(3)}s</span>
                            </div>
                          )}
                        </div>
                      )}
                    </GlassCard>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="px-5 py-4 border-t border-[var(--color-border-subtle)] flex gap-3">
          <AnansiButton
            variant="secondary"
            size="md"
            icon={<Play className="h-4 w-4" />}
            fullWidth
            feedbackState={isRunning ? "loading" : "idle"}
            onClick={handleRunTest}
          >
            Test (Dry Run)
          </AnansiButton>

          {stepThrough && (
            <AnansiButton
              variant="primary"
              size="md"
              icon={<SkipForward className="h-4 w-4" />}
              fullWidth
              disabled={!isRunningState}
            >
              Next Step
            </AnansiButton>
          )}

          {!stepThrough && (
            <AnansiButton
              variant="primary"
              size="md"
              icon={<Play className="h-4 w-4" />}
              fullWidth
              disabled={!agentId}
              feedbackState={isRunning ? "loading" : "idle"}
              onClick={handleRun}
            >
              Run (Live)
            </AnansiButton>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Client-side test simulation ────────────────────────────────────────────────

async function simulateTestRun(
  definition: { blocks: Array<{ id: string; type: string; subtype: string; config: Record<string, unknown> }>; edges: Array<{ source: string; target: string }> },
  inputData: Record<string, unknown>,
): Promise<AgentRun> {
  const startTime = Date.now();
  const steps: Array<Record<string, unknown>> = [];
  const { blocks, edges } = definition;

  if (!blocks || blocks.length === 0) {
    return {
      id: `test-${Date.now()}`,
      agentId: "test",
      userId: "test",
      triggerType: "manual",
      status: "completed",
      inputData,
      outputData: {},
      errorMessage: null,
      steps: [],
      memoryNodesCreated: 0,
      memoryLinksCreated: 0,
      startedAt: new Date().toISOString(),
      completedAt: new Date().toISOString(),
      durationMs: 0,
      costCents: 0,
    };
  }

  // Build execution order via topological sort
  const adj: Record<string, string[]> = {};
  const inDeg: Record<string, number> = {};
  for (const b of blocks) {
    adj[b.id] = [];
    inDeg[b.id] = 0;
  }
  for (const e of edges) {
    if (adj[e.source]) {
      adj[e.source].push(e.target);
      inDeg[e.target] = (inDeg[e.target] || 0) + 1;
    }
  }

  const queue = Object.keys(inDeg).filter((id) => inDeg[id] === 0);
  const order: string[] = [];
  while (queue.length) {
    const node = queue.shift()!;
    order.push(node);
    for (const neighbor of adj[node] || []) {
      inDeg[neighbor] -= 1;
      if (inDeg[neighbor] === 0) queue.push(neighbor);
    }
  }

  let hasErrors = false;
  let outputData: Record<string, unknown> = { ...inputData };

  for (const blockId of order) {
    const block = blocks.find((b) => b.id === blockId);
    if (!block) continue;

    const stepStart = Date.now();
    const stepEntry: Record<string, unknown> = {
      block_id: blockId,
      block_type: block.type,
      block_subtype: block.subtype,
      status: "running",
      started_at: new Date(stepStart).toISOString(),
    };

    try {
      // Simulate block execution based on type
      const mockOutput = simulateBlockOutput(block, outputData);
      await sleep(100); // Simulate processing time

      outputData[blockId] = mockOutput;
      stepEntry.status = "completed";
      stepEntry.output = mockOutput;
      stepEntry.duration_ms = Date.now() - stepStart;
    } catch (err) {
      hasErrors = true;
      stepEntry.status = "error";
      stepEntry.error = err instanceof Error ? err.message : "Block execution failed";
      stepEntry.duration_ms = Date.now() - stepStart;
    }

    steps.push(stepEntry);
  }

  const totalDuration = Date.now() - startTime;

  return {
    id: `test-${Date.now()}`,
    agentId: "test",
    userId: "test",
    triggerType: "manual",
    status: hasErrors ? "completed_with_errors" : "completed",
    inputData,
    outputData,
    errorMessage: hasErrors ? "Some blocks had errors" : null,
    steps,
    memoryNodesCreated: Math.floor(steps.length * 1.5),
    memoryLinksCreated: steps.length,
    startedAt: new Date(startTime).toISOString(),
    completedAt: new Date(Date.now()).toISOString(),
    durationMs: totalDuration,
    costCents: 0,
  };
}

function simulateBlockOutput(
  block: { type: string; subtype: string; config: Record<string, unknown> },
  input: Record<string, unknown>,
): Record<string, unknown> {
  const { type, subtype, config } = block;

  if (type === "trigger") {
    return { triggered_at: new Date().toISOString() };
  }
  if (type === "ai") {
    if (subtype === "conversation") return { response: `[TEST] AI response`, model: config.model || "default" };
    if (subtype === "extract") return { extracted: { result: "test" } };
    if (subtype === "classify") return { classification: "test", confidence: 0.9 };
    if (subtype === "summarize") return { summary: "[TEST] Simulated summary" };
    if (subtype === "generate") return { generated: "[TEST] Generated content" };
    if (subtype === "transform") return { transformed: "[TEST] Transformed" };
    return { result: "[TEST] AI output" };
  }
  if (type === "action") {
    return { status: "simulated", action: subtype, test_mode: true };
  }
  if (type === "logic") {
    if (subtype === "condition") {
      const expr = (config.expression as string) || "True";
      return { condition_result: true, branch: "true" };
    }
    if (subtype === "delay") return { delayed_seconds: 0 };
    if (subtype === "loop") return { items: [], total_items: 0 };
    if (subtype === "filter") return { original_count: 0, filtered_count: 0, items: [] };
    if (subtype === "router") return { matched: false, case_label: "default" };
    return {};
  }
  return {};
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
