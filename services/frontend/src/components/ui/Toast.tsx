"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui";
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import type { ToastType } from "@/types";

const toastIcons: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle className="h-5 w-5 text-semantic-success-light" />,
  error: <AlertCircle className="h-5 w-5 text-semantic-error-light" />,
  warning: <AlertTriangle className="h-5 w-5 text-semantic-warning-light" />,
  info: <Info className="h-5 w-5 text-semantic-info-light" />,
};

const toastBorders: Record<ToastType, string> = {
  success: "border-l-semantic-success",
  error: "border-l-semantic-error",
  warning: "border-l-semantic-warning",
  info: "border-l-semantic-info",
};

function ToastItem({
  id,
  type,
  title,
  message,
  onDismiss,
}: {
  id: string;
  type: ToastType;
  title: string;
  message?: string;
  onDismiss: (id: string) => void;
}) {
  const [isVisible, setIsVisible] = useState(false);
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    // Trigger enter animation on next frame
    const enterTimer = requestAnimationFrame(() => setIsVisible(true));
    return () => cancelAnimationFrame(enterTimer);
  }, []);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(id), 200);
  };

  return (
    <div
      role="alert"
      aria-live="polite"
      className={cn(
        "flex items-start gap-3 glass-elevated rounded-lg px-4 py-3 min-w-[320px] max-w-[420px]",
        "border-l-4",
        toastBorders[type],
        "transition-all duration-200 ease-anansi",
        isVisible && !isExiting ? "translate-x-0 opacity-100" : "translate-x-full opacity-0",
        isExiting && "translate-x-full opacity-0",
      )}
    >
      <span className="shrink-0 mt-0.5">{toastIcons[type]}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{title}</p>
        {message && (
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{message}</p>
        )}
      </div>
      <button
        onClick={handleDismiss}
        className="shrink-0 p-0.5 rounded text-[var(--color-text-disabled)] hover:text-[var(--color-text-primary)] transition-colors"
        aria-label="Dismiss notification"
        type="button"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts);
  const removeToast = useUIStore((s) => s.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
      aria-label="Notifications"
    >
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <ToastItem
            id={toast.id}
            type={toast.type}
            title={toast.title}
            message={toast.message}
            onDismiss={removeToast}
          />
        </div>
      ))}
    </div>
  );
}
