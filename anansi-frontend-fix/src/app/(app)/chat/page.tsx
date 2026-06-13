"use client";

import { useState, useRef, useEffect } from "react";
import { AIThread } from "../../../components/features/AIThread";
import { GlassCard } from "../../../components/ui/GlassCard";
import { Input } from "../../../components/ui/Input";
import { AnansiButton } from "../../../components/ui/AnansiButton";
import { BrainIcon } from "../../../components/ui/BrainIcon";
import { useChatStore } from "../../../stores/chat";
import {
  Send,
  Mic,
  Paperclip,
  PanelRightClose,
  PanelRightOpen,
  Sparkles,
  Brain,
  X,
  MessageSquare,
} from "lucide-react";
import { cn } from "../../../lib/utils";

const suggestedPrompts = [
  "What's on my calendar today?",
  "Summarize my unread emails",
  "Create a follow-up agent for new leads",
  "What did I learn last week?",
  "Draft a reply to James about the project",
];

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [contextOpen, setContextOpen] = useState(true);
  const inputRef = useRef<HTMLInputElement>(null);

  const {
    conversations,
    activeConversationId,
    isStreaming,
    streamingMessage,
    sendMessage,
    setActiveConversation,
    createNewConversation,
  } = useChatStore();

  const activeConversation = conversations.find(
    (c) => c.id === activeConversationId,
  );

  const handleSend = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="flex h-[calc(100vh-3.5rem-3rem)] -mx-6 lg:-mx-8 -mb-6 lg:-mb-8">
      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-[var(--color-border-subtle)]">
          <div className="flex items-center gap-3">
            <BrainIcon size={20} active={isStreaming} glow="amber" />
            <div>
              <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
                {activeConversation?.title ?? "AI Chat"}
              </h2>
              {isStreaming && (
                <span className="text-xs text-brand-amber-light">Anansi is responding...</span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setContextOpen(!contextOpen)}
              className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors hidden lg:block"
              aria-label={contextOpen ? "Close context panel" : "Open context panel"}
              type="button"
            >
              {contextOpen ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-hidden">
          <AIThread
            messages={activeConversation?.messages ?? []}
            streamingMessage={streamingMessage}
            isStreaming={isStreaming}
            onWikilinkClick={(target) => {
              // Stub — will navigate to memory detail
              console.log("Navigate to memory:", target);
            }}
          />
        </div>

        {/* Input area */}
        <div className="border-t border-[var(--color-border-subtle)] px-4 py-4">
          {/* Suggested prompts */}
          {!activeConversation?.messages?.length && !isStreaming && (
            <div className="mb-4">
              <p className="text-xs text-[var(--color-text-muted)] mb-2 flex items-center gap-1">
                <Sparkles className="h-3 w-3" />
                Suggested prompts
              </p>
              <div className="flex flex-wrap gap-2">
                {suggestedPrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => {
                      sendMessage(prompt);
                    }}
                    className="px-3 py-1.5 rounded-full text-xs text-[var(--color-text-secondary)] bg-white/5 border border-[var(--color-border-subtle)] hover:border-amber-500/30 hover:text-[var(--color-text-primary)] transition-all duration-200 ease-anansi"
                    type="button"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input bar */}
          <div className="flex items-end gap-2">
            <div className="flex-1 relative">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask Anansi anything..."
                className="pr-20"
                disabled={isStreaming}
              />
              <div className="absolute right-2 bottom-1.5 flex items-center gap-1">
                <button
                  className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
                  aria-label="Upload file"
                  type="button"
                >
                  <Paperclip className="h-4 w-4" />
                </button>
                <button
                  className="p-1.5 rounded-md text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 transition-colors"
                  aria-label="Voice input"
                  type="button"
                >
                  <Mic className="h-4 w-4" />
                </button>
              </div>
            </div>
            <AnansiButton
              variant="primary"
              size="md"
              onClick={handleSend}
              disabled={!input.trim() || isStreaming}
              icon={<Send className="h-4 w-4" />}
            >
              Send
            </AnansiButton>
          </div>
        </div>
      </div>

      {/* Context panel (right sidebar) */}
      {contextOpen && (
        <aside className="hidden lg:flex w-72 flex-col border-l border-[var(--color-border-subtle)]">
          <div className="px-4 py-3 border-b border-[var(--color-border-subtle)]">
            <h3 className="text-sm font-semibold text-[var(--color-text-primary)] flex items-center gap-2">
              <Brain className="h-4 w-4 text-brand-amber-light" />
              Context
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {/* Related memories */}
            <div>
              <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                Related Memories
              </p>
              <div className="space-y-2">
                {[
                  "Email workflow preferences",
                  "Client: James — Project Alpha",
                  "Q2 Revenue Goal",
                ].map((memory) => (
                  <button
                    key={memory}
                    className="w-full text-left px-3 py-2 rounded-lg text-sm text-[var(--color-text-secondary)] bg-white/5 hover:bg-white/10 transition-colors"
                    type="button"
                  >
                    <span className="text-brand-amber-light">[[</span>
                    {memory}
                    <span className="text-brand-amber-light">]]</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Active tools */}
            <div>
              <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                Active Tools
              </p>
              <div className="space-y-1">
                {["Gmail (read)", "Calendar (read)", "Memory (write)"].map((tool) => (
                  <div
                    key={tool}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs text-[var(--color-text-secondary)]"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-semantic-success-light" />
                    {tool}
                  </div>
                ))}
              </div>
            </div>

            {/* New memories being created */}
            <div>
              <p className="text-xs font-medium text-[var(--color-text-muted)] uppercase tracking-wider mb-2">
                Creating Memories
              </p>
              <div className="space-y-1">
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/5 border border-amber-500/10 animate-pulse">
                  <BrainIcon size={12} active glow="amber" />
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    Linking to related nodes...
                  </span>
                </div>
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
