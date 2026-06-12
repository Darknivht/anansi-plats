import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type GlassVariant = "base" | "elevated" | "interactive";
type GlowColor = "amber" | "violet" | "teal" | "none";
type PaddingSize = "sm" | "md" | "lg";

interface GlassCardProps {
  variant?: GlassVariant;
  glow?: GlowColor;
  padding?: PaddingSize;
  className?: string;
  onClick?: () => void;
  children: ReactNode;
}

const variantClasses: Record<GlassVariant, string> = {
  base: "glass-card",
  elevated: "glass-elevated",
  interactive: "glass-interactive",
};

const glowClasses: Record<GlowColor, string> = {
  amber: "glow-amber border-amber-500/20",
  violet: "glow-violet border-violet-500/20",
  teal: "glow-teal border-teal-500/20",
  none: "",
};

const paddingClasses: Record<PaddingSize, string> = {
  sm: "p-4",
  md: "p-6",
  lg: "p-8",
};

export function GlassCard({
  variant = "base",
  glow = "none",
  padding = "md",
  className,
  onClick,
  children,
}: GlassCardProps) {
  const Component = onClick ? "button" : "div";

  return (
    <Component
      className={cn(
        variantClasses[variant],
        glow !== "none" && glowClasses[glow],
        paddingClasses[padding],
        onClick && "cursor-pointer text-left w-full",
        className,
      )}
      onClick={onClick}
      {...(onClick ? { type: "button" as const } : {})}
    >
      {children}
    </Component>
  );
}

interface GlassCardHeaderProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardHeader({ className, children }: GlassCardHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between mb-4", className)}>
      {children}
    </div>
  );
}

interface GlassCardTitleProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardTitle({ className, children }: GlassCardTitleProps) {
  return (
    <h3 className={cn("text-lg font-heading font-bold text-[var(--color-text-primary)]", className)}>
      {children}
    </h3>
  );
}

interface GlassCardContentProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardContent({ className, children }: GlassCardContentProps) {
  return <div className={cn(className)}>{children}</div>;
}

interface GlassCardActionProps {
  className?: string;
  children: ReactNode;
}

export function GlassCardAction({ className, children }: GlassCardActionProps) {
  return <div className={cn("flex items-center gap-2", className)}>{children}</div>;
}
