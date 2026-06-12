import { type InputHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  icon?: React.ReactNode;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, icon, className, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-sm font-medium text-[var(--color-text-secondary)] mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none text-[var(--color-text-muted)]">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              "w-full rounded-lg px-4 py-2.5 text-sm",
              "bg-[var(--glass-interactive-bg)] backdrop-blur-[16px]",
              "border border-[var(--color-border-subtle)]",
              "text-[var(--color-text-primary)] placeholder:text-[var(--color-text-disabled)]",
              "transition-all duration-200 ease-anansi",
              "focus:outline-none focus:border-amber-500/40 focus:ring-1 focus:ring-amber-500/20",
              "hover:border-[var(--color-border-subtle)]/80",
              error && "border-semantic-error focus:border-semantic-error focus:ring-semantic-error/20",
              icon && "pl-10",
              className,
            )}
            aria-invalid={!!error}
            aria-describedby={error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined}
            {...props}
          />
        </div>
        {error && (
          <p id={`${inputId}-error`} className="mt-1.5 text-xs text-semantic-error" role="alert">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${inputId}-helper`} className="mt-1.5 text-xs text-[var(--color-text-muted)]">
            {helperText}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
