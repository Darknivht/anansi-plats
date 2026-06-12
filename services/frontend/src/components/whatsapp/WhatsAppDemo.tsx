"use client";

import { useState, useRef, useEffect } from "react";
import { cn } from "@/lib/utils";
import {
  Phone,
  MessageCircle,
  Mic,
  Play,
  Send,
  Check,
  Brain,
  Sun,
  ListChecks,
  HelpCircle,
  BarChart3,
  Share2,
  Image,
} from "lucide-react";

// ── Types ──

interface ChatMessage {
  id: string;
  role: "user" | "bot";
  text: string;
  timestamp: Date;
  type?: "text" | "command" | "voice" | "system" | "image";
  status?: "sent" | "delivered" | "read";
}

// ── Demo Messages ──

const DEMO_MESSAGES: ChatMessage[] = [
  {
    id: "m1",
    role: "bot",
    text: "👋 Welcome to Anansi! I'm your AI, connected to your Second Brain. Try a command or just chat with me!",
    timestamp: new Date(Date.now() - 120000),
    type: "system",
  },
  {
    id: "m2",
    role: "user",
    text: "/briefing",
    timestamp: new Date(Date.now() - 110000),
    type: "command",
  },
  {
    id: "m3",
    role: "bot",
    text: "🌅 *Good Morning!*\n\n📅 Monday, June 15, 2026\n\n📊 *Your Second Brain*\n• 147 memories (12 new this week)\n• 389 connections (28 new this week)\n• 3 reviews due\n\n📅 *Today's Schedule*\n• 10:00 AM — Design Review\n• 2:00 PM — Client Call (James)\n• 4:00 PM — Gym\n\n💡 *Tip:* You have 5 unread emails from the Design team — want a summary?",
    timestamp: new Date(Date.now() - 105000),
  },
  {
    id: "m4",
    role: "user",
    text: "/record Sold 20 yards of Ankara to Mama Grace for ₦45,000",
    timestamp: new Date(Date.now() - 90000),
    type: "command",
  },
  {
    id: "m5",
    role: "bot",
    text: "✅ *Recorded!*\n📝 Sale: 20 yards Ankara print to Mama Grace\n💰 Amount: ₦45,000\n🏷️ #transaction #sale\n\n🔗 Linked to [[Customer: Mama Grace]]\n📦 Updated inventory: 15 yards remaining\n\n📊 *Pro tip:* Check your sales summary with `/summary sales`",
    timestamp: new Date(Date.now() - 87000),
  },
  {
    id: "m6",
    role: "user",
    text: "🎤 [Voice note: 12 seconds]",
    timestamp: new Date(Date.now() - 70000),
    type: "voice",
  },
  {
    id: "m7",
    role: "bot",
    text: "🎤 *Voice note transcribed:*\n\"Can you remind me to call James about the invoice tomorrow at 10am?\"\n\n✅ *Reminder set:* Call James about invoice — Tomorrow, 10:00 AM\n\n🧠 Saved to your Second Brain as a task.",
    timestamp: new Date(Date.now() - 65000),
  },
  {
    id: "m8",
    role: "user",
    text: "/graph",
    timestamp: new Date(Date.now() - 45000),
    type: "command",
  },
  {
    id: "m9",
    role: "bot",
    text: "🌐 *Your Knowledge Web*\n\n📊 147 nodes · 389 connections\n\n📁 *By Type:*\n• Fact: 62\n• Preference: 28\n• Pattern: 24\n• Relation: 18\n• Daily Note: 15\n\n🔗 *Most Connected:*\n• Client Orders (8 connections)\n• Mama Grace (6 connections)\n• Invoice Workflow (5 connections)\n\n📸 *Graph visualization available in the web app!*",
    timestamp: new Date(Date.now() - 42000),
  },
  {
    id: "m10",
    role: "bot",
    text: "🧠 *Brain Insight*\n\nI noticed a connection between your recent sales to Mama Grace and an increase in Ankara print orders. Your inventory is running low — consider restocking soon! 📈",
    timestamp: new Date(Date.now() - 20000),
    type: "system",
  },
];

// ── Quick Action Buttons ──

const QUICK_ACTIONS = [
  { label: "/briefing", icon: Sun, desc: "Morning briefing" },
  { label: "/tasks", icon: ListChecks, desc: "Today's tasks" },
  { label: "/record", icon: Mic, desc: "Log something" },
  { label: "/graph", icon: Share2, desc: "Brain snapshot" },
  { label: "/brain", icon: Brain, desc: "Brain stats" },
  { label: "/help", icon: HelpCircle, desc: "All commands" },
];

// ── Typing Indicator ──

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2 mb-4">
      <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-amber to-brand-amber-light flex items-center justify-center text-white text-xs font-bold shrink-0">
        A
      </div>
      <div className="bg-[#1a1a1a] rounded-lg rounded-tl-none px-4 py-3 max-w-[80%]">
        <div className="flex items-center gap-1">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="w-2 h-2 rounded-full bg-amber-500 inline-block"
              style={{
                animation: "typingBounce 1.4s ease-in-out infinite",
                animationDelay: `${i * 0.2}s`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ──

export default function WhatsAppDemo() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [inputText, setInputText] = useState("");
  const [demoStep, setDemoStep] = useState(0);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const typingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Auto-play demo ──

  useEffect(() => {
    if (demoStep >= DEMO_MESSAGES.length) return;

    const timer = setTimeout(() => {
      const msg = DEMO_MESSAGES[demoStep];

      if (msg.role === "bot") {
        setIsTyping(true);

        typingTimerRef.current = setTimeout(() => {
          setIsTyping(false);
          setMessages((prev) => [...prev, msg]);
          setDemoStep((s) => s + 1);
        }, msg.text.length > 200 ? 2500 : 1200);
      } else {
        setMessages((prev) => [...prev, msg]);
        setDemoStep((s) => s + 1);
      }
    }, demoStep === 0 ? 500 : 1800);

    return () => {
      clearTimeout(timer);
      if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    };
  }, [demoStep]);

  // ── Auto-scroll ──

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // ── Format message text (support bold with * markers) ──

  const formatMessage = (text: string) => {
    return text.split(/\n/).map((line, i) => {
      // Bold segments
      const parts = line.split(/(\*[^*]+\*)/g);
      return (
        <span key={i}>
          {i > 0 && <br />}
          {parts.map((part, j) => {
            if (part.startsWith("*") && part.endsWith("*")) {
              return (
                <strong key={j} className="font-semibold text-[var(--color-text-primary)]">
                  {part.slice(1, -1)}
                </strong>
              );
            }
            return <span key={j}>{part}</span>;
          })}
        </span>
      );
    });
  };

  // ── Reset demo ──

  const handleReset = () => {
    setMessages([]);
    setDemoStep(0);
    setIsTyping(false);
    if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
  };

  // ── Send message (in demo, just adds to chat) ──

  const handleSend = () => {
    if (!inputText.trim()) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      text: inputText.trim(),
      timestamp: new Date(),
      type: inputText.startsWith("/") ? "command" : "text",
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText("");

    // Simulate bot response
    setIsTyping(true);
    setTimeout(() => {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          role: "bot",
          text: "Thanks for your message! This is a demo — try the auto-play to see all the features in action, or check the real thing in settings! 🕷️",
          timestamp: new Date(),
        },
      ]);
    }, 1500);
  };

  // ── Handle key press ──

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Render ──

  return (
    <div className="flex flex-col h-full bg-[#0a0a0a] rounded-xl overflow-hidden border border-[var(--color-border-subtle)]">
      {/* Chat Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border-subtle)] bg-[#111]">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-full bg-gradient-to-br from-brand-amber to-brand-amber-light flex items-center justify-center">
            <span className="text-white text-sm font-bold">A</span>
          </div>
          <div>
            <p className="text-sm font-medium text-[var(--color-text-primary)]">Anansi AI</p>
            <p className="text-xs text-emerald-400 flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 inline-block" />
              Online
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="px-3 py-1.5 text-xs rounded-lg bg-[var(--glass-interactive-bg)] border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
            type="button"
          >
            ↺ Restart
          </button>
          <Play className="h-4 w-4 text-[var(--color-text-muted)]" />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-1 scrollbar-thin">
        {messages.length === 0 && demoStep === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-12">
            <MessageCircle className="h-12 w-12 text-brand-amber-light/30 mb-4" />
            <p className="text-[var(--color-text-muted)] text-sm mb-2">
              WhatsApp Chat Demo
            </p>
            <p className="text-[var(--color-text-disabled)] text-xs mb-6 max-w-xs">
              Watch the auto-play demo showing Anansi&apos;s WhatsApp features —
              commands, voice notes, brain insights, and more.
            </p>
            <div className="flex flex-wrap gap-2 justify-center max-w-sm">
              {QUICK_ACTIONS.slice(0, 4).map((action) => (
                <button
                  key={action.label}
                  className="px-3 py-1.5 text-xs rounded-full bg-amber-500/10 border border-amber-500/20 text-brand-amber-light hover:bg-amber-500/20 transition-colors"
                  type="button"
                >
                  {action.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex items-start gap-2 mb-4",
              msg.role === "user" ? "flex-row-reverse" : "",
            )}
          >
            {/* Avatar */}
            {msg.role === "bot" && (
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-amber to-brand-amber-light flex items-center justify-center text-white text-xs font-bold shrink-0">
                A
              </div>
            )}

            {/* Message Bubble */}
            <div
              className={cn(
                "rounded-lg px-4 py-2.5 max-w-[80%] text-sm leading-relaxed",
                msg.role === "user"
                  ? "bg-gradient-to-r from-brand-amber to-brand-amber-light text-white rounded-tr-none"
                  : "bg-[#1a1a1a] text-[var(--color-text-secondary)] rounded-tl-none",
                msg.type === "command" && msg.role === "user" && "font-mono text-xs",
                msg.type === "system" && msg.role === "bot" && "border-l-2 border-violet-500/50",
                msg.type === "voice" && msg.role === "user" && "bg-brand-amber/20",
              )}
            >
              {/* Voice note indicator */}
              {msg.type === "voice" && msg.role === "user" && (
                <div className="flex items-center gap-2 mb-1">
                  <div className="flex items-center gap-0.5">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className="w-0.5 bg-white/60 rounded-full"
                        style={{
                          height: `${8 + Math.random() * 12}px`,
                          animation: "voiceWave 0.8s ease-in-out infinite",
                          animationDelay: `${i * 0.1}s`,
                        }}
                      />
                    ))}
                  </div>
                  <span className="text-xs text-white/70">{msg.text}</span>
                </div>
              )}

              {/* Normal text */}
              {msg.type !== "voice" && formatMessage(msg.text)}

              {/* Timestamp + Status */}
              <div
                className={cn(
                  "flex items-center gap-1 mt-1",
                  msg.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <span className="text-[10px] opacity-50">
                  {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                {msg.role === "user" && (
                  <Check className="h-3 w-3 text-white/40" />
                )}
              </div>
            </div>
          </div>
        ))}

        {isTyping && <TypingIndicator />}

        <div ref={chatEndRef} />
      </div>

      {/* Quick Actions Bar */}
      <div className="px-3 py-2 border-t border-[var(--color-border-subtle)] bg-[#111]">
        <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-thin">
          {QUICK_ACTIONS.map((action) => (
            <button
              key={action.label}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs whitespace-nowrap bg-[var(--glass-interactive-bg)] border border-[var(--color-border-subtle)] text-[var(--color-text-muted)] hover:text-brand-amber-light hover:border-amber-500/20 transition-colors shrink-0"
              type="button"
              title={action.desc}
            >
              <action.icon className="h-3 w-3" />
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input Area */}
      <div className="flex items-center gap-2 px-4 py-3 border-t border-[var(--color-border-subtle)] bg-[#111]">
        <button
          className="h-9 w-9 rounded-full flex items-center justify-center text-[var(--color-text-muted)] hover:text-brand-amber-light transition-colors"
          type="button"
        >
          <Mic className="h-5 w-5" />
        </button>
        <div className="flex-1 relative">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="w-full rounded-lg px-4 py-2 text-sm bg-[#1a1a1a] border border-[var(--color-border-subtle)] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-disabled)] focus:outline-none focus:border-amber-500/40 focus:ring-1 focus:ring-amber-500/20 transition-all"
          />
        </div>
        <button
          onClick={handleSend}
          disabled={!inputText.trim()}
          className={cn(
            "h-9 w-9 rounded-full flex items-center justify-center transition-all",
            inputText.trim()
              ? "bg-gradient-to-r from-brand-amber to-brand-amber-light text-white"
              : "bg-[var(--color-border-subtle)] text-[var(--color-text-disabled)]",
          )}
          type="button"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      {/* Animations */}
      <style jsx global>{`
        @keyframes typingBounce {
          0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
          30% { opacity: 1; transform: translateY(-4px); }
        }
        @keyframes voiceWave {
          0%, 100% { transform: scaleY(0.5); }
          50% { transform: scaleY(1); }
        }
        .scrollbar-thin::-webkit-scrollbar {
          width: 4px;
        }
        .scrollbar-thin::-webkit-scrollbar-track {
          background: transparent;
        }
        .scrollbar-thin::-webkit-scrollbar-thumb {
          background: rgba(68, 64, 60, 0.5);
          border-radius: 2px;
        }
      `}</style>
    </div>
  );
}
