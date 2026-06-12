import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "success" | "warning" | "error" | "info" | "brand";

interface BadgeProps {
  variant?: BadgeVariant;
  size?: "sm" | "md";
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  /**
   * Make the badge a pill shape (fully rounded)
   */
  pill?: boolean;
}

const variantClasses: Record<BadgeVariant, string> = {
  success:
    "bg-semantic-success/10 text-semantic-success-light border-semantic-success/20",
  warning:
    "bg-semantic-warning/10 text-semantic-warning-light border-semantic-warning/20",
  error:
    "bg-semantic-error/10 text-semantic-error-light border-semantic-error/20",
  info: "bg-semantic-info/10 text-semantic-info-light border-semantic-info/20",
  brand:
    "bg-brand-amber/10 text-brand-amber-light border-brand-amber/20",
};

const sizeClasses: Record<string, string> = {
  sm: "px-2 py-0.5 text-xs",
  md: "px-2.5 py-1 text-xs",
};

/**
 * Status badge component with semantic colors.
 */
export function Badge({
  variant = "brand",
  size = "sm",
  icon,
  children,
  className,
  pill = true,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 font-medium border",
        pill ? "rounded-full" : "rounded-md",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </span>
  );
}
