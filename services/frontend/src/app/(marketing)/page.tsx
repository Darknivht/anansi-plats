"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { GlassCard } from "@/components/ui/GlassCard";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { BrainIcon } from "@/components/ui/BrainIcon";
import {
  Brain,
  Bot,
  Network,
  Sparkles,
  Zap,
  Shield,
  Check,
  ArrowRight,
  Star,
} from "lucide-react";

// ── Feature cards data ──
const features = [
  {
    icon: <Brain className="h-6 w-6" />,
    title: "Second Brain Memory",
    description:
      "Every interaction builds your knowledge web. Anansi remembers, links, and summarizes everything — just like Obsidian but alive with AI.",
    color: "text-brand-amber-light",
    glow: "amber" as const,
  },
  {
    icon: <Bot className="h-6 w-6" />,
    title: "Personal AI Agents",
    description:
      "Create custom AI agents with drag-and-drop. No coding needed. Agents read your email, manage tasks, and take action across your tools.",
    color: "text-brand-violet-light",
    glow: "violet" as const,
  },
  {
    icon: <Network className="h-6 w-6" />,
    title: "Connected Knowledge Web",
    description:
      "Bidirectional links between every memory, agent output, and document. Explore your life as an interactive graph — just like Obsidian's graph view.",
    color: "text-brand-teal-light",
    glow: "teal" as const,
  },
  {
    icon: <Zap className="h-6 w-6" />,
    title: "WhatsApp-Native AI",
    description:
      "Talk to your AI on WhatsApp. Voice notes, quick commands, and pro-active updates. Your AI works wherever you are.",
    color: "text-brand-amber-light",
    glow: "amber" as const,
  },
  {
    icon: <Shield className="h-6 w-6" />,
    title: "200+ Integrations",
    description:
      "Connect Gmail, Google Calendar, Slack, Notion, GitHub, and more. Your AI orchestrates all your tools through one unified interface.",
    color: "text-brand-violet-light",
    glow: "violet" as const,
  },
];

// ── Pricing plans ──
const plans = [
  {
    name: "Free",
    price: "$0",
    period: "/month",
    description: "Perfect for getting started",
    features: [
      "1,000 memory nodes",
      "5 agents",
      "5 integrations",
      "Basic auto-linking",
      "Layer 1 summarization",
      "Chat with AI",
    ],
    cta: "Get Started",
    href: "/signup",
    highlighted: false,
  },
  {
    name: "Pro",
    price: "$19",
    period: "/month",
    description: "For professionals and power users",
    features: [
      "10,000 memory nodes",
      "Unlimited agents",
      "Unlimited integrations",
      "Advanced auto-linking",
      "All 4 summarization layers",
      "Spaced repetition reviews",
      "Brain export (Obsidian)",
      "WhatsApp priority",
    ],
    cta: "Start Free Trial",
    href: "/signup?plan=pro",
    highlighted: true,
  },
  {
    name: "Business",
    price: "$99",
    period: "/month",
    description: "For teams and organizations",
    features: [
      "Unlimited memory nodes",
      "Unlimited agents",
      "Unlimited integrations",
      "Full auto-linking + custom rules",
      "All summarization layers",
      "Unlimited reviews",
      "Team management (up to 50)",
      "Enterprise connectors",
      "Priority support",
      "Custom brain export",
    ],
    cta: "Contact Sales",
    href: "/signup?plan=business",
    highlighted: false,
  },
];

export default function LandingPage() {
  return (
    <div className="relative">
      {/* ── HERO SECTION ── */}
      <section className="relative min-h-[90vh] flex flex-col items-center justify-center px-4 py-20 overflow-hidden">
        {/* Ambient background */}
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-amber/5 rounded-full blur-[128px]" />
          <div className="absolute bottom-1/3 right-1/4 w-80 h-80 bg-brand-violet/5 rounded-full blur-[128px]" />
        </div>

        <div className="relative z-10 max-w-4xl mx-auto text-center">
          {/* Brain icon */}
          <div className="mb-8 flex justify-center">
            <BrainIcon size={64} active glow="amber" />
          </div>

          {/* Tagline */}
          <h1 className="text-5xl sm:text-6xl lg:text-7xl font-heading font-extrabold tracking-tight text-[var(--color-text-primary)] leading-[1.05]">
            Your AI.
            <br />
            <span className="bg-gradient-to-r from-brand-amber to-brand-amber-light bg-clip-text text-transparent">
              Your Life.
            </span>
            <br />
            Your OS.
          </h1>

          <p className="mt-6 text-lg sm:text-xl text-[var(--color-text-secondary)] max-w-2xl mx-auto leading-relaxed">
            Not just a chatbot — a true{" "}
            <span className="text-brand-amber-light font-semibold">Second Brain</span>{" "}
            that learns, links, and grows with you. Anansi weaves your work, business,
            and personal life into one AI-native experience.
          </p>

          {/* CTA Buttons */}
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <AnansiButton variant="primary" size="lg" icon={<Sparkles className="h-5 w-5" />}>
                Start Building Your Second Brain
              </AnansiButton>
            </Link>
            <Link href="#features">
              <AnansiButton variant="secondary" size="lg" icon={<Brain className="h-5 w-5" />}>
                See How It Works
              </AnansiButton>
            </Link>
          </div>

          {/* Social proof */}
          <div className="mt-12 flex items-center justify-center gap-2 text-sm text-[var(--color-text-muted)]">
            <div className="flex -space-x-2">
              {[1, 2, 3, 4].map((i) => (
                <div
                  key={i}
                  className="h-8 w-8 rounded-full border-2 border-[var(--color-bg-deepest)] bg-gradient-to-br from-brand-amber/30 to-brand-violet/30"
                />
              ))}
            </div>
            <span>
              Join <strong className="text-[var(--color-text-primary)]">early adopters</strong> building
              their Second Brain
            </span>
          </div>
        </div>
      </section>

      {/* ── SECOND BRAIN SECTION ── */}
      <section className="relative px-4 py-24 border-t border-[var(--color-border-subtle)]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-[var(--color-text-primary)]">
              Your AI builds a{" "}
              <span className="text-brand-amber-light">Second Brain</span> as you work
            </h2>
            <p className="mt-4 text-lg text-[var(--color-text-secondary)] max-w-2xl mx-auto">
              Every conversation, every email, every task gets linked into a growing
              knowledge web — discoverable, searchable, and alive with connections.
            </p>
          </div>

          {/* Knowledge web visualization placeholder */}
          <GlassCard variant="elevated" glow="amber" padding="lg" className="relative overflow-hidden">
            <div className="absolute inset-0 opacity-10 pointer-events-none">
              {/* Decorative web pattern */}
              <svg viewBox="0 0 800 400" className="w-full h-full">
                <line x1="400" y1="200" x2="100" y2="50" stroke="#F59E0B" strokeWidth="0.5" />
                <line x1="400" y1="200" x2="700" y2="50" stroke="#F59E0B" strokeWidth="0.5" />
                <line x1="400" y1="200" x2="100" y2="350" stroke="#F59E0B" strokeWidth="0.5" />
                <line x1="400" y1="200" x2="700" y2="350" stroke="#F59E0B" strokeWidth="0.5" />
                <line x1="400" y1="200" x2="50" y2="200" stroke="#F59E0B" strokeWidth="0.5" />
                <line x1="400" y1="200" x2="750" y2="200" stroke="#F59E0B" strokeWidth="0.5" />
                <circle cx="400" cy="200" r="30" fill="none" stroke="#F59E0B" strokeWidth="0.5" />
              </svg>
            </div>

            <div className="relative z-10 flex flex-col md:flex-row items-center gap-8">
              <div className="flex-1">
                <h3 className="text-xl font-heading font-bold text-[var(--color-text-primary)] mb-4">
                  Inspired by Obsidian, powered by AI
                </h3>
                <ul className="space-y-3">
                  {[
                    { icon: <Network className="h-4 w-4" />, text: "Bidirectional [[wikilinks]] between every memory" },
                    { icon: <Sparkles className="h-4 w-4" />, text: "Progressive Summarization at 4 levels" },
                    { icon: <Brain className="h-4 w-4" />, text: "Zettelkasten-style atomic knowledge nodes" },
                    { icon: <Zap className="h-4 w-4" />, text: "Spaced Repetition for long-term retention" },
                  ].map((item) => (
                    <li key={item.text} className="flex items-center gap-3 text-sm text-[var(--color-text-secondary)]">
                      <span className="text-brand-amber-light shrink-0">{item.icon}</span>
                      <span>{item.text}</span>
                    </li>
                  ))}
                </ul>
              </div>
              <div className="flex-1">
                <GlassCard variant="base" padding="md" className="text-sm">
                  <div className="text-xs text-[var(--color-text-muted)] mb-2">Today's Memory Overview</div>
                  <div className="space-y-2">
                    <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Knowledge nodes</span><span className="text-brand-amber-light font-semibold">47</span></div>
                    <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Bidirectional links</span><span className="text-brand-teal-light font-semibold">128</span></div>
                    <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">New today</span><span className="text-semantic-success-light font-semibold">+5 nodes, +12 links</span></div>
                    <div className="flex justify-between"><span className="text-[var(--color-text-secondary)]">Top cluster</span><span className="text-[var(--color-text-primary)]">Work</span></div>
                  </div>
                </GlassCard>
              </div>
            </div>
          </GlassCard>
        </div>
      </section>

      {/* ── FEATURES SECTION ── */}
      <section id="features" className="relative px-4 py-24 border-t border-[var(--color-border-subtle)]">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-[var(--color-text-primary)]">
              Everything you need for your{" "}
              <span className="text-brand-amber-light">digital life</span>
            </h2>
            <p className="mt-4 text-lg text-[var(--color-text-muted)] max-w-2xl mx-auto">
              Five interconnected layers that work together seamlessly.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, i) => (
              <FeatureCard key={feature.title} feature={feature} index={i} />
            ))}
          </div>
        </div>
      </section>

      {/* ── PRICING SECTION ── */}
      <section id="pricing" className="relative px-4 py-24 border-t border-[var(--color-border-subtle)]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-heading font-bold text-[var(--color-text-primary)]">
              Choose your{" "}
              <span className="text-brand-amber-light">Second Brain</span> plan
            </h2>
            <p className="mt-4 text-lg text-[var(--color-text-muted)]">
              Start free. Upgrade when your brain grows.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <GlassCard
                key={plan.name}
                variant={plan.highlighted ? "elevated" : "base"}
                glow={plan.highlighted ? "amber" : "none"}
                padding="lg"
                className={cn(
                  "flex flex-col",
                  plan.highlighted && "relative scale-105 border-amber-500/40",
                )}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full bg-gradient-to-r from-brand-amber to-brand-amber-light text-xs font-semibold text-white">
                    Most Popular
                  </div>
                )}

                <div className="mb-6">
                  <h3 className="text-xl font-heading font-bold text-[var(--color-text-primary)]">
                    {plan.name}
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)] mt-1">
                    {plan.description}
                  </p>
                </div>

                <div className="mb-6">
                  <span className="text-4xl font-heading font-extrabold text-[var(--color-text-primary)]">
                    {plan.price}
                  </span>
                  <span className="text-sm text-[var(--color-text-muted)]">{plan.period}</span>
                </div>

                <ul className="flex-1 space-y-2.5 mb-8">
                  {plan.features.map((feat) => (
                    <li key={feat} className="flex items-start gap-2 text-sm text-[var(--color-text-secondary)]">
                      <Check className="h-4 w-4 text-semantic-success-light shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>

                <Link href={plan.href}>
                  <AnansiButton
                    variant={plan.highlighted ? "primary" : "secondary"}
                    fullWidth
                    size="lg"
                  >
                    {plan.cta}
                  </AnansiButton>
                </Link>
              </GlassCard>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA SECTION ── */}
      <section className="relative px-4 py-24 border-t border-[var(--color-border-subtle)]">
        <div className="max-w-3xl mx-auto text-center">
          <BrainIcon size={56} active glow="amber" />
          <h2 className="mt-6 text-3xl sm:text-4xl font-heading font-bold text-[var(--color-text-primary)]">
            Ready to build your{" "}
            <span className="text-brand-amber-light">Second Brain</span>?
          </h2>
          <p className="mt-4 text-lg text-[var(--color-text-secondary)]">
            Join thousands of early adopters who are already weaving their digital lives
            with Anansi. Free to start. No credit card required.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/signup">
              <AnansiButton variant="primary" size="lg" icon={<Sparkles className="h-5 w-5" />}>
                Start Free — No Credit Card
              </AnansiButton>
            </Link>
            <Link href="#features">
              <AnansiButton variant="secondary" size="lg">
                Learn More
                <ArrowRight className="h-4 w-4" />
              </AnansiButton>
            </Link>
          </div>
        </div>
      </section>

      {/* ── FOOTER ── */}
      <footer className="border-t border-[var(--color-border-subtle)] px-4 py-12">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-8">
            {/* Logo */}
            <div className="flex items-center gap-2">
              <BrainIcon size={20} active={false} />
              <span className="text-sm font-heading font-bold text-[var(--color-text-primary)]">
                anansi
              </span>
            </div>

            {/* Links */}
            <div className="flex flex-wrap justify-center gap-6 text-sm">
              <a href="#features" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                Features
              </a>
              <a href="#pricing" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                Pricing
              </a>
              <a href="/login" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                Log in
              </a>
              <a href="/signup" className="text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors">
                Sign up
              </a>
            </div>

            {/* Copyright */}
            <p className="text-xs text-[var(--color-text-disabled)]">
              &copy; {new Date().getFullYear()} Anansi. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

// ── Feature Card Component with scroll reveal ──

function FeatureCard({
  feature,
  index,
}: {
  feature: (typeof features)[number];
  index: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold: 0.1, rootMargin: "-50px" },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      style={{ transitionDelay: `${index * 100}ms` }}
      className={cn(
        "transition-all duration-600 ease-anansi",
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8",
      )}
    >
      <GlassCard variant="interactive" glow={feature.glow} padding="lg" className="h-full">
        <div className={cn("h-12 w-12 rounded-xl flex items-center justify-center mb-4", "bg-white/5 border border-white/10")}>
          <span className={feature.color}>{feature.icon}</span>
        </div>
        <h3 className="text-lg font-heading font-bold text-[var(--color-text-primary)] mb-2">
          {feature.title}
        </h3>
        <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
          {feature.description}
        </p>
      </GlassCard>
    </div>
  );
}
