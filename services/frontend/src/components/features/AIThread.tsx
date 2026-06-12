"use client";

import { type ReactNode, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import { BrainIcon } from "@/components/ui/BrainIcon";
import { Wikilink } from "@/components/ui/Wikilink";
import { GlassCard } from "@/components/ui/GlassCard";
import { parseWikilink } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import type { Message, StreamingMessage } from "@/types";

interface AIThreadProps {
  messages: Message[];
  streamingMessage?: StreamingMessage | null;
  isStreaming?: boolean;
  className?: string;
  onWikilinkClick?: (target: string) => void;
  emptyState?: ReactNode;
}

/**
 * Renders a thread of AI conversation messages with proper styling.
 * Supports streaming response display, memory references via [[wikilinks]],
 * and typing indicators.
 */
export function AIThread({
  messages,
  streamingMessage,
  isStreaming = false,
  className,
  onWikilinkClick,
  emptyState,
}: AIThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages and streaming
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingMessage?.content]);

  if (messages.length === 0 && !streamingMessage && !isStreaming) {
    return (
      <div className={cn("flex items-center justify-center h-full", className)}>
        {emptyState ?? (
          <div className="text-center max-w-md">
            <BrainIcon size={48} active glow="amber" />
            <h3 className="mt-4 text-lg font-heading font-bold text-[var(--color-text-primary)]">
              Chat with Anansi
            </h3>
            <p className="mt-2 text-sm text-[var(--color-text-muted)]">
              Ask me anything — I can help with tasks, answer questions, or just chat.
              I remember our conversations and build a knowledge web as we talk.
            </p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className={cn(
        "flex flex-col gap-4 overflow-y-auto px-4 py-6",
        className,
      )}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      {/* Rendered messages */}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onWikilinkClick={onWikilinkClick} />
      ))}

      {/* Streaming message */}
      {streamingMessage && streamingMessage.content && (
        <div className="flex items-start gap-3">
          <BrainIcon size={20} active glow="amber" />
          <GlassCard variant="base" padding="md" className="flex-1 max-w-[80%]">
            <StreamingContent content={streamingMessage.content} onWikilinkClick={onWikilinkClick} />
          </GlassCard>
        </div>
      )}

      {/* Typing indicator */}
      {isStreaming && !streamingMessage?.content && (
        <div className="flex items-start gap-3">
          <BrainIcon size={20} active glow="amber" />
          <GlassCard variant="base" padding="md" className="flex items-center gap-2">
            <div className="flex gap-1">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="h-2 w-2 rounded-full bg-brand-amber-light inline-block"
                  style={{
                    animation: `typing-dot 1.2s ease-in-out ${i * 0.2}s infinite`,
                  }}
                />
              ))}
            </div>
            <span className="text-xs text-[var(--color-text-muted)] ml-1">
              Anansi is thinking...
            </span>
          </GlassCard>
        </div>
      )}
    </div>
  );
}

// ── Individual message bubble ──

function MessageBubble({
  message,
  onWikilinkClick,
}: {
  message: Message;
  onWikilinkClick?: (target: string) => void;
}) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <span className="text-xs text-[var(--color-text-muted)] px-3 py-1 rounded-full bg-white/5">
          {message.content}
        </span>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%]">
          <div className="px-4 py-2.5 rounded-2xl bg-gradient-to-r from-brand-amber/20 to-brand-amber/10 text-sm text-[var(--color-text-primary)] border border-amber-500/20">
            <MessageContent content={message.content} onWikilinkClick={onWikilinkClick} />
          </div>
          {message.referencedMemoryNodes.length > 0 && (
            <div className="flex justify-end gap-1 mt-1">
              {message.referencedMemoryNodes.map((node) => (
                <Wikilink key={node} target={node} size="sm" />
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // AI message
  return (
    <div className="flex items-start gap-3">
      <BrainIcon size={20} active={false} className="mt-1" />
      <GlassCard variant="base" padding="md" className="flex-1 max-w-[80%]">
        <MessageContent content={message.content} onWikilinkClick={onWikilinkClick} />
        {message.referencedMemoryNodes.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2 pt-2 border-t border-[var(--color-border-subtle)]">
            {message.referencedMemoryNodes.map((node) => (
              <Wikilink key={node} target={node} onWikilinkClick={onWikilinkClick} />
            ))}
          </div>
        )}
      </GlassCard>
    </div>
  );
}

// ── Message content with wikilink parsing ──

function MessageContent({
  content,
  onWikilinkClick,
}: {
  content: string;
  onWikilinkClick?: (target: string) => void;
}) {
  const wikilinks = parseWikilink(content);

  if (wikilinks.length === 0) {
    return <p className="text-sm whitespace-pre-wrap leading-relaxed">{content}</p>;
  }

  // Split content by wikilinks and render inline
  const parts = content.split(/(\[\[[^\]]+\]\])/g);
  return (
    <p className="text-sm whitespace-pre-wrap leading-relaxed">
      {parts.map((part, i) => {
        const match = part.match(/^\[\[([^\]]+)\]\]$/);
        if (match && match[1]) {
          return (
            <Wikilink
              key={i}
              target={match[1]}
              onClick={onWikilinkClick}
              className="inline-flex mx-0.5"
            />
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </p>
  );
}

// ── Streaming content with word-by-word fade-in ──

function StreamingContent({
  content,
  onWikilinkClick,
}: {
  content: string;
  onWikilinkClick?: (target: string) => void;
}) {
  const wikilinks = parseWikilink(content);

  if (wikilinks.length === 0) {
    return (
      <p className="text-sm whitespace-pre-wrap leading-relaxed">
        {content}
        <span className="inline-block h-4 w-0.5 bg-brand-amber-light animate-pulse ml-0.5" />
      </p>
    );
  }

  const parts = content.split(/(\[\[[^\]]+\]\])/g);
  return (
    <p className="text-sm whitespace-pre-wrap leading-relaxed">
      {parts.map((part, i) => {
        const match = part.match(/^\[\[([^\]]+)\]\]$/);
        if (match && match[1]) {
          return (
            <Wikilink
              key={i}
              target={match[1]}
              onClick={onWikilinkClick}
              className="inline-flex mx-0.5"
            />
          );
        }
        return <span key={i}>{part}</span>;
      })}
      <span className="inline-block h-4 w-0.5 bg-brand-amber-light animate-pulse ml-0.5" />
    </p>
  );
}
