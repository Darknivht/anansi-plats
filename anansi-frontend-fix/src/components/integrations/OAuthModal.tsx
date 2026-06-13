"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { cn } from "../../lib/utils";
import { Input } from "../../components/ui/Input";
import { useIntegrationStore, type ConnectorWithStatus } from "../../stores/integrations";
import { useUIStore } from "../../stores/ui";

// ─── Props ────────────────────────────────────────────────────────────────

interface OAuthModalProps {
  connector: ConnectorWithStatus;
  onClose: () => void;
  onSuccess?: () => void;
}

// ─── Component ────────────────────────────────────────────────────────────

export function OAuthModal({ connector, onClose, onSuccess }: OAuthModalProps) {
  const [step, setStep] = useState<"form" | "loading" | "success" | "error">("form");
  const [apiKey, setApiKey] = useState("");
  const [configValues, setConfigValues] = useState<Record<string, string>>({});
  const [errorMsg, setErrorMsg] = useState("");
  const popupRef = useRef<Window | null>(null);
  const popupTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const initiateOAuth = useIntegrationStore((s) => s.initiateOAuth);
  const connectApiKey = useIntegrationStore((s) => s.connectApiKey);
  const handleOAuthCallback = useIntegrationStore((s) => s.handleOAuthCallback);
  const addToast = useUIStore((s) => s.addToast);

  // ── Cleanup on unmount ──
  useEffect(() => {
    return () => {
      if (popupTimerRef.current) clearInterval(popupTimerRef.current);
      if (popupRef.current && !popupRef.current.closed) popupRef.current.close();
    };
  }, []);

  // ── OAuth flow handler ──
  const handleOAuth = useCallback(async () => {
    setStep("loading");
    setErrorMsg("");

    try {
      // The OAuth redirect URI — this should point back to the app
      const redirectUri = `${window.location.origin}/integrations/oauth/callback`;

      const result = await initiateOAuth(connector.key, redirectUri);
      if (!result) {
        throw new Error("Failed to start OAuth flow");
      }

      // Open OAuth window
      const popup = window.open(
        result.authUrl,
        `oauth-${connector.key}`,
        "width=600,height=700,scrollbars=yes,resizable=yes"
      );

      if (!popup) {
        // Popup blocked — redirect instead
        window.location.href = result.authUrl;
        return;
      }

      popupRef.current = popup;

      // Poll the popup for the callback code
      // In production, use window.postMessage or a dedicated callback page
      popupTimerRef.current = setInterval(async () => {
        if (popup.closed) {
          clearInterval(popupTimerRef.current!);
          setStep("error");
          setErrorMsg("OAuth window closed. Please try again.");
          return;
        }

        try {
          // Check if the popup navigated to our callback URL
          const popupUrl = popup.document.URL;
          if (popupUrl && popupUrl.includes("/integrations/oauth/callback")) {
            const url = new URL(popupUrl);
            const code = url.searchParams.get("code");
            const state = url.searchParams.get("state");

            if (code && state) {
              clearInterval(popupTimerRef.current!);
              popup.close();

              const success = await handleOAuthCallback(connector.key, code, state);
              if (success) {
                setStep("success");
                addToast("success", `${connector.name} connected successfully!`);
                setTimeout(() => {
                  onSuccess?.();
                  onClose();
                }, 1500);
              } else {
                setStep("error");
                setErrorMsg("Failed to complete OAuth. Please try again.");
              }
            }
          }
        } catch {
          // Cross-origin errors are expected while popup is on the OAuth provider's domain
        }
      }, 500);
    } catch (err) {
      setStep("error");
      setErrorMsg(err instanceof Error ? err.message : "OAuth failed");
    }
  }, [connector, initiateOAuth, handleOAuthCallback, addToast, onClose, onSuccess]);

  // ── API Key flow handler ──
  const handleApiKeyConnect = useCallback(async () => {
    setStep("loading");
    setErrorMsg("");

    if (!apiKey.trim()) {
      setStep("error");
      setErrorMsg("Please enter an API key");
      return;
    }

    try {
      const config: Record<string, unknown> = { ...configValues };
      const success = await connectApiKey(connector.key, apiKey.trim(), config);

      if (success) {
        setStep("success");
        addToast("success", `${connector.name} connected successfully!`);
        setTimeout(() => {
          onSuccess?.();
          onClose();
        }, 1500);
      } else {
        setStep("error");
        setErrorMsg("Failed to connect. Please check your API key.");
      }
    } catch (err) {
      setStep("error");
      setErrorMsg(err instanceof Error ? err.message : "Connection failed");
    }
  }, [connector, apiKey, configValues, connectApiKey, addToast, onClose, onSuccess]);

  // ── Render ──

  const isOAuth = connector.authType === "oauth2";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className={cn(
          "relative w-full max-w-md rounded-2xl border p-6 shadow-2xl",
          "bg-[var(--color-bg-elevated)] dark:bg-[var(--color-bg-elevated)]",
          "border-[var(--color-border)] dark:border-white/10",
        )}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-[var(--color-text-tertiary)] transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6L6 18M6 6l12 12" />
          </svg>
        </button>

        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-lg bg-[var(--color-bg-deepest)] dark:bg-white/5 flex items-center justify-center text-xl">
            {connector.iconUrl ? (
              <img src={connector.iconUrl} alt={connector.name} className="w-6 h-6" />
            ) : (
              <span>{connector.name[0]}</span>
            )}
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-text-primary)] dark:text-white">
              Connect {connector.name}
            </h2>
            <p className="text-sm text-[var(--color-text-tertiary)] dark:text-white/50">
              {isOAuth ? "Authorize with OAuth" : "Enter your API key"}
            </p>
          </div>
        </div>

        {/* Body */}
        {step === "form" && (
          <div className="space-y-4">
            {isOAuth ? (
              <div className="text-sm text-[var(--color-text-secondary)] dark:text-white/70 mb-4">
                <p>You&apos;ll be redirected to {connector.name} to authorize access.</p>
                <p className="mt-2 text-xs text-[var(--color-text-tertiary)] dark:text-white/50">
                  Anansi will receive: read &amp; write access to your {connector.name} data as needed.
                  You can revoke access anytime.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-[var(--color-text-primary)] dark:text-white mb-1">
                    API Key
                  </label>
                  <Input
                    type="password"
                    value={apiKey}
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setApiKey(e.target.value)}
                    placeholder={`Enter your ${connector.name} API key`}
                    className="w-full"
                  />
                </div>

                {/* Extra config fields for services that need them */}
                {connector.key === "whatsapp" && (
                  <div>
                    <label className="block text-sm font-medium text-[var(--color-text-primary)] dark:text-white mb-1">
                      Phone Number ID
                    </label>
                    <Input
                      type="text"
                      value={configValues.phone_number_id ?? ""}
                      onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                        setConfigValues((prev) => ({ ...prev, phone_number_id: e.target.value }))
                      }
                      placeholder="WhatsApp Business Phone Number ID"
                      className="w-full"
                    />
                  </div>
                )}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-[var(--color-border)] dark:border-white/10 text-[var(--color-text-secondary)] dark:text-white/70 hover:bg-white/5"
              >
                Cancel
              </button>
              <button
                onClick={isOAuth ? handleOAuth : handleApiKeyConnect}
                className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-bg-cta)] text-white hover:opacity-90"
              >
                {isOAuth ? "Continue with OAuth" : "Connect"}
              </button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {step === "loading" && (
          <div className="flex flex-col items-center py-8 gap-3">
            <div className="w-10 h-10 border-2 border-[var(--color-brand-primary)] border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-[var(--color-text-secondary)] dark:text-white/70">
              {isOAuth
                ? "Waiting for authorization..."
                : `Connecting to ${connector.name}...`}
            </p>
          </div>
        )}

        {/* Success State */}
        {step === "success" && (
          <div className="flex flex-col items-center py-8 gap-2">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 flex items-center justify-center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <p className="text-sm font-medium text-emerald-500">Connected successfully!</p>
          </div>
        )}

        {/* Error State */}
        {step === "error" && (
          <div className="space-y-4">
            <div className="flex flex-col items-center py-4 gap-2">
              <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M15 9l-6 6M9 9l6 6" />
                </svg>
              </div>
              <p className="text-sm text-red-400 text-center">{errorMsg || "Connection failed"}</p>
            </div>
            <button
              onClick={() => setStep("form")}
              className="w-full px-4 py-2 rounded-lg text-sm font-medium bg-[var(--color-bg-cta)] text-white hover:opacity-90"
            >
              Try Again
            </button>
          </div>
        )}
      </div>
    </div>
  );
}