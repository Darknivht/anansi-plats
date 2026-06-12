"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { AnansiButton } from "@/components/ui/AnansiButton";
import {
  X,
  Check,
  AlertCircle,
  Loader2,
  Download,
  ArrowRight,
  Sparkles,
} from "lucide-react";
import type { MarketplaceListing } from "@/stores/marketplace";

// ─── Install Modal ───────────────────────────────────────────────────────────

interface InstallModalProps {
  listing: MarketplaceListing | null;
  isOpen: boolean;
  isInstalling: boolean;
  onClose: () => void;
  onConfirm: () => Promise<void>;
  hasInstalled?: boolean;
}

export function InstallModal({
  listing,
  isOpen,
  isInstalling,
  onClose,
  onConfirm,
  hasInstalled = false,
}: InstallModalProps) {
  const router = useRouter();
  const [step, setStep] = useState<"confirm" | "installing" | "success" | "error">("confirm");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [installedAgentId, setInstalledAgentId] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setStep(hasInstalled ? "success" : "confirm");
      setErrorMessage(null);
    } else {
      // Reset after close animation
      const timer = setTimeout(() => {
        setStep("confirm");
        setErrorMessage(null);
        setInstalledAgentId(null);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen, hasInstalled]);

  const handleInstall = useCallback(async () => {
    setStep("installing");
    setErrorMessage(null);

    try {
      const result = await onConfirm();
      setStep("success");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Installation failed";
      setErrorMessage(message);
      setStep("error");
    }
  }, [onConfirm]);

  const handleViewAgent = useCallback(() => {
    if (installedAgentId) {
      router.push(`/agents/${installedAgentId}`);
    } else {
      router.push("/agents");
    }
    onClose();
  }, [installedAgentId, router, onClose]);

  const handleGoToWorkshop = useCallback(() => {
    router.push("/agents/new/canvas");
    onClose();
  }, [router, onClose]);

  if (!isOpen || !listing) return null;

  const priceDisplay =
    listing.price_cents === 0
      ? "Free"
      : `$${(listing.price_cents / 100).toFixed(2)}`;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div
        className={cn(
          "relative w-full max-w-md",
          "bg-[var(--color-bg-surface)]/90 backdrop-blur-2xl",
          "border border-[var(--color-border-subtle)]",
          "rounded-2xl shadow-xl overflow-hidden",
          "animate-in fade-in zoom-in-95 duration-200"
        )}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1 rounded-lg hover:bg-white/5 text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        {/* Content */}
        <div className="p-6">
          {/* ── Confirm Step ── */}
          {step === "confirm" && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="h-12 w-12 rounded-xl bg-gradient-to-br from-[var(--color-brand-amber)]/20 to-[var(--color-spirit-violet)]/20 flex items-center justify-center">
                  <Download className="h-6 w-6 text-[var(--color-brand-amber)]" />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
                    Install Agent
                  </h3>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {priceDisplay} &middot; {listing.category || "Uncategorized"}
                  </p>
                </div>
              </div>

              {/* Agent info */}
              <div className="bg-[var(--color-bg-deepest)]/40 rounded-lg p-4 space-y-2">
                <p className="font-medium text-[var(--color-text-primary)]">
                  {listing.title}
                </p>
                <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">
                  {listing.description || "No description provided."}
                </p>
                <div className="flex items-center gap-4 text-xs text-[var(--color-text-muted)]">
                  <span>v{listing.agent_version || "1.0"}</span>
                  <span>{listing.install_count} installs</span>
                  <span>{listing.rating_count} reviews</span>
                </div>
              </div>

              {/* What happens */}
              <div className="text-sm text-[var(--color-text-secondary)] space-y-1.5">
                <p className="font-medium text-[var(--color-text-primary)]">
                  What happens when you install:
                </p>
                <ul className="space-y-1 list-disc list-inside text-xs">
                  <li>A copy of this agent is added to your library</li>
                  <li>You can customize it in the Workshop</li>
                  <li>Your version is independent of the original</li>
                </ul>
              </div>

              {/* Actions */}
              <div className="flex gap-2 pt-2">
                <AnansiButton
                  variant="ghost"
                  size="md"
                  onClick={onClose}
                  className="flex-1"
                >
                  Cancel
                </AnansiButton>
                <AnansiButton
                  variant="primary"
                  size="md"
                  onClick={handleInstall}
                  disabled={isInstalling}
                  className="flex-1"
                >
                  {isInstalling ? "Installing..." : `Install ${priceDisplay !== "Free" ? `- ${priceDisplay}` : ""}`}
                </AnansiButton>
              </div>
            </div>
          )}

          {/* ── Installing Step ── */}
          {step === "installing" && (
            <div className="py-12 text-center space-y-4">
              <Loader2 className="h-12 w-12 animate-spin mx-auto text-[var(--color-brand-amber)]" />
              <div>
                <h3 className="text-lg font-semibold text-[var(--color-text-primary)]">
                  Installing Agent
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  Creating a copy in your library...
                </p>
              </div>
              <div className="w-48 h-1.5 mx-auto bg-[var(--color-bg-deepest)] rounded-full overflow-hidden">
                <div className="h-full w-2/3 bg-gradient-to-r from-[var(--color-brand-amber)] to-[var(--color-brand-amber-light)] rounded-full animate-pulse" />
              </div>
            </div>
          )}

          {/* ── Success Step ── */}
          {step === "success" && (
            <div className="py-8 text-center space-y-4">
              <div className="h-16 w-16 rounded-full bg-emerald-500/20 mx-auto flex items-center justify-center">
                <Check className="h-8 w-8 text-emerald-400" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
                  {hasInstalled ? "Already Installed" : "Agent Installed!"}
                </h3>
                <p className="text-sm text-[var(--color-text-muted)] mt-1">
                  {hasInstalled
                    ? "You already have this agent in your library."
                    : `"${listing.title}" has been added to your library.`}
                </p>
              </div>
              <div className="flex gap-2 justify-center pt-2">
                <AnansiButton variant="ghost" size="sm" onClick={onClose}>
                  Close
                </AnansiButton>
                <AnansiButton
                  variant="primary"
                  size="sm"
                  icon={<ArrowRight className="h-4 w-4" />}
                  onClick={handleGoToWorkshop}
                >
                  Open in Workshop
                </AnansiButton>
              </div>
            </div>
          )}

          {/* ── Error Step ── */}
          {step === "error" && (
            <div className="py-8 text-center space-y-4">
              <div className="h-16 w-16 rounded-full bg-red-500/20 mx-auto flex items-center justify-center">
                <AlertCircle className="h-8 w-8 text-red-400" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-[var(--color-text-primary)]">
                  Installation Failed
                </h3>
                <p className="text-sm text-red-400 mt-1">
                  {errorMessage || "Something went wrong. Please try again."}
                </p>
              </div>
              <div className="flex gap-2 justify-center pt-2">
                <AnansiButton variant="ghost" size="sm" onClick={onClose}>
                  Cancel
                </AnansiButton>
                <AnansiButton
                  variant="primary"
                  size="sm"
                  onClick={handleInstall}
                >
                  Try Again
                </AnansiButton>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
