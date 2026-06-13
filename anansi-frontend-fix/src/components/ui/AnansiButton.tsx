"use client";

import { type ButtonHTMLAttributes, type ReactNode, useRef, useState } from "react";
import { cn } from "../../lib/utils";
import { Loader2, Check, X } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";
type FeedbackState = "idle" | "loading" | "success" | "error";

interface AnansiButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
  feedbackState?: FeedbackState;
  fullWidth?: boolean;
  children: ReactNode;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-gradient-to-r from-brand-amber to-brand-amber-light text-white font-semibold shadow-glow-amber hover:shadow-[0_0_30px_rgba(245,158,11,0.25)] active:scale-[0.97]",
  secondary:
    "glass-interactive text-[var(--color-text-primary)] border border-[var(--color-border-subtle)] hover:border-amber-500/30 hover:bg-amber-500/5",
  ghost:
    "bg-transparent text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-white/5",
  danger:
    "bg-gradient-to-r from-red-600 to-red-500 text-white font-semibold hover:shadow-[0_0_30px_rgba(220,38,38,0.25)] active:scale-[0.97]",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm gap-1.5",
  md: "px-5 py-2.5 text-sm gap-2",
  lg: "px-8 py-3.5 text-base gap-2.5",
};

const iconSizeClasses: Record<ButtonSize, string> = {
  sm: "h-4 w-4",
  md: "h-4 w-4",
  lg: "h-5 w-5",
};

const feedbackIcons: Record<FeedbackState, ReactNode | null> = {
  idle: null,
  loading: <Loader2 className="animate-spin" />,
  success: <Check />,
  error: <X />,
};

export function AnansiButton({
  variant = "primary",
  size = "md",
  icon,
  feedbackState = "idle",
  fullWidth = false,
  className,
  children,
  disabled,
  ...props
}: AnansiButtonProps) {
  const [internalState, setInternalState] = useState<FeedbackState>("idle");
  const currentState = feedbackState !== "idle" ? feedbackState : internalState;
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleClick = async (e: React.MouseEvent<HTMLButtonElement>) => {
    if (currentState === "loading") return;

    // Allow the parent onClick to run, then auto-detect feedback
    // if a promise-returning onClick isn't provided
    props.onClick?.(e as unknown as React.MouseEvent<HTMLButtonElement>);
  };

  const showTemporaryState = (state: "success" | "error") => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setInternalState(state);
    timeoutRef.current = setTimeout(() => {
      setInternalState("idle");
    }, 2000);
  };

  const isDisabled = disabled || currentState === "loading";
  const FeedbackIcon = feedbackIcons[currentState];

  return (
    <button
      className={cn(
        "relative inline-flex items-center justify-center rounded-lg font-medium",
        "transition-all duration-200 ease-anansi",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-amber-500",
        "disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none",
        variantClasses[variant],
        sizeClasses[size],
        fullWidth && "w-full",
        currentState === "success" && "!from-semantic-success !to-semantic-success-light",
        currentState === "error" && "!from-semantic-error !to-semantic-error-light",
        className,
      )}
      disabled={isDisabled}
      onClick={handleClick}
      type="button"
      aria-busy={currentState === "loading"}
      {...props}
    >
      {FeedbackIcon && (
        <span className={cn(iconSizeClasses[size], "shrink-0")}>
          {FeedbackIcon}
        </span>
      )}
      {!FeedbackIcon && icon && (
        <span className={cn(iconSizeClasses[size], "shrink-0")}>{icon}</span>
      )}
      <span className={cn(currentState === "loading" && "opacity-80")}>
        {children}
      </span>
    </button>
  );
}
