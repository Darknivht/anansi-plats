"use client";

import { useState, useEffect, useCallback } from "react";
import { GlassCard, GlassCardHeader, GlassCardTitle } from "../../../../components/ui/GlassCard";
import { Input } from "../../../../components/ui/Input";
import { AnansiButton } from "../../../../components/ui/AnansiButton";
import { Badge } from "../../../../components/ui/Badge";
import { cn } from "../../../../lib/utils";
import { api } from "../../../../lib/api";
import {
  MessageCircle,
  Check,
  X,
  Loader2,
  Send,
  ChevronDown,
  ChevronUp,
  Bell,
  BellOff,
  Sun,
  Zap,
  AlertTriangle,
  Lightbulb,
  Calendar,
  BookOpen,
  Brain,
  Trash2,
  Smartphone,
  Copy,
} from "lucide-react";

// ── Types ──

interface WhatsAppStatus {
  connected: boolean;
  phone_number: string | null;
  status: string;
  verified_at: string | null;
  settings: Record<string, boolean>;
}

interface NotificationSetting {
  key: string;
  label: string;
  description: string;
  icon: React.ReactNode;
}

const NOTIFICATION_SETTINGS: NotificationSetting[] = [
  {
    key: "notify_morning_briefing",
    label: "Morning Briefing",
    description: "Daily AI summary at 7am",
    icon: <Sun className="h-4 w-4" />,
  },
  {
    key: "notify_agent_completed",
    label: "Agent Completed",
    description: "When an agent finishes running",
    icon: <Zap className="h-4 w-4" />,
  },
  {
    key: "notify_alerts",
    label: "Alerts",
    description: "Something needs your attention",
    icon: <AlertTriangle className="h-4 w-4" />,
  },
  {
    key: "notify_suggestions",
    label: "Suggestions",
    description: "AI proactive suggestions",
    icon: <Lightbulb className="h-4 w-4" />,
  },
  {
    key: "notify_weekly_summary",
    label: "Weekly Summary",
    description: "Sunday evening week recap",
    icon: <Calendar className="h-4 w-4" />,
  },
  {
    key: "notify_review_reminder",
    label: "Review Reminders",
    description: "Spaced repetition due items",
    icon: <BookOpen className="h-4 w-4" />,
  },
  {
    key: "notify_brain_insight",
    label: "Brain Insights",
    description: "AI-discovered connections",
    icon: <Brain className="h-4 w-4" />,
  },
];

// ── Toggle Switch ──

function Toggle({
  enabled,
  onChange,
  label,
  description,
  icon,
}: {
  enabled: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
  icon?: React.ReactNode;
}) {
  return (
    <label className="flex items-center justify-between py-3 px-3 rounded-lg hover:bg-white/5 transition-colors cursor-pointer group">
      <div className="flex items-center gap-3">
        {icon && (
          <span
            className={cn(
              "transition-colors",
              enabled ? "text-brand-amber-light" : "text-[var(--color-text-muted)]",
            )}
          >
            {icon}
          </span>
        )}
        <div>
          <p className="text-sm font-medium text-[var(--color-text-primary)]">{label}</p>
          {description && (
            <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
          )}
        </div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={(e) => {
          e.preventDefault();
          onChange(!enabled);
        }}
        className={cn(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200",
          enabled
            ? "bg-gradient-to-r from-brand-amber to-brand-amber-light"
            : "bg-[var(--color-border-subtle)]",
        )}
      >
        <span
          className={cn(
            "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200",
            enabled ? "translate-x-4.5" : "translate-x-1",
          )}
        />
      </button>
    </label>
  );
}

// ── Settings Section ──

function SettingsSection({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <GlassCard variant="base" padding="md" className="mb-6">
      <GlassCardHeader>
        <div>
          <GlassCardTitle>{title}</GlassCardTitle>
          {description && (
            <p className="text-xs text-[var(--color-text-muted)] mt-0.5">{description}</p>
          )}
        </div>
      </GlassCardHeader>
      <div className="space-y-1">{children}</div>
    </GlassCard>
  );
}

// ── OTP Input ──

function OtpInput({
  length = 6,
  value,
  onChange,
  disabled = false,
}: {
  length?: number;
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
}) {
  const digits = value.split("").concat(Array(length - value.length).fill(""));

  return (
    <div className="flex gap-2 justify-center my-4">
      {digits.map((digit, idx) => (
        <div
          key={idx}
          className={cn(
            "w-10 h-12 flex items-center justify-center rounded-lg text-lg font-mono font-bold",
            "border transition-all duration-150",
            digit
              ? "border-brand-amber-light/50 bg-brand-amber/10 text-brand-amber-light"
              : "border-[var(--color-border-subtle)] bg-[var(--glass-interactive-bg)] text-[var(--color-text-muted)]",
            disabled && "opacity-50",
          )}
        >
          {digit || ""}
        </div>
      ))}
    </div>
  );
}

// ── Status Badge ──

function ConnectionStatusBadge({ status }: { status: string }) {
  const config: Record<string, { label: string; variant: "success" | "warning" | "error" | "info" }> = {
    active: { label: "Connected", variant: "success" },
    pending: { label: "Pending", variant: "warning" },
    disconnected: { label: "Disconnected", variant: "error" },
    expired: { label: "Expired", variant: "warning" },
  };

  const cfg = config[status] ?? { label: status, variant: "info" as const };
  return <Badge variant={cfg.variant} size="sm">{cfg.label}</Badge>;
}

// ── Main Component ──

export default function WhatsAppSettings() {
  // State
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState<WhatsAppStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Linking flow
  const [phoneNumber, setPhoneNumber] = useState("");
  const [linking, setLinking] = useState(false);
  const [linkError, setLinkError] = useState<string | null>(null);

  // OTP verification
  const [showOtp, setShowOtp] = useState(false);
  const [otpCode, setOtpCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [verifyError, setVerifyError] = useState<string | null>(null);
  const [otpTimer, setOtpTimer] = useState(0);

  // Notification preferences
  const [notifSettings, setNotifSettings] = useState<Record<string, boolean>>({});
  const [savingSettings, setSavingSettings] = useState(false);

  // Test message
  const [sendingTest, setSendingTest] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  // Disconnect
  const [showDisconnectConfirm, setShowDisconnectConfirm] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  // ── Fetch Status ──

  const fetchStatus = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.get<WhatsAppStatus>("/api/v1/whatsapp/status");
      setStatus(data);
      setNotifSettings(data.settings || {});
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load status";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // ── OTP Timer ──

  useEffect(() => {
    if (otpTimer <= 0) return;
    const interval = setInterval(() => {
      setOtpTimer((t) => {
        if (t <= 1) {
          clearInterval(interval);
          return 0;
        }
        return t - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [otpTimer]);

  // ── Link Number ──

  const handleLink = async () => {
    if (!phoneNumber || phoneNumber.length < 8) {
      setLinkError("Please enter a valid phone number (e.g., +2348012345678)");
      return;
    }

    try {
      setLinking(true);
      setLinkError(null);
      setVerifyError(null);

      const result = await api.post<{ status: string; message: string; expires_in: number }>(
        "/api/v1/whatsapp/link",
        { phone_number: phoneNumber },
      );

      setShowOtp(true);
      setOtpTimer(result.expires_in);
      setOtpCode("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send verification code";
      setLinkError(msg);
    } finally {
      setLinking(false);
    }
  };

  // ── Verify OTP ──

  const handleVerify = async () => {
    if (otpCode.length !== 6) {
      setVerifyError("Please enter the full 6-digit code");
      return;
    }

    try {
      setVerifying(true);
      setVerifyError(null);

      await api.post<{ status: string; message: string }>("/api/v1/whatsapp/verify", {
        code: otpCode,
      });

      // Refresh status
      await fetchStatus();
      setShowOtp(false);
      setOtpCode("");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Invalid verification code";
      setVerifyError(msg);
    } finally {
      setVerifying(false);
    }
  };

  // ── Update Settings ──

  const handleToggleSetting = async (key: string, value: boolean) => {
    const newSettings = { ...notifSettings, [key]: value };
    setNotifSettings(newSettings);

    try {
      setSavingSettings(true);
      await api.patch("/api/v1/whatsapp/settings", { [key]: value });
    } catch (err: unknown) {
      // Revert on error
      setNotifSettings(notifSettings);
      console.error("Failed to update setting:", err);
    } finally {
      setSavingSettings(false);
    }
  };

  // ── Send Test Message ──

  const handleSendTest = async () => {
    try {
      setSendingTest(true);
      setTestResult(null);

      const result = await api.post<{ sent: boolean; message: string }>("/api/v1/whatsapp/test");
      setTestResult(result.sent ? "✅ Message sent! Check your WhatsApp." : `❌ ${result.message}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to send test message";
      setTestResult(`❌ ${msg}`);
    } finally {
      setSendingTest(false);
    }
  };

  // ── Disconnect ──

  const handleDisconnect = async () => {
    try {
      setDisconnecting(true);
      await api.post("/api/v1/whatsapp/unlink");
      setStatus(null);
      setShowDisconnectConfirm(false);
      setPhoneNumber("");
      setShowOtp(false);
      setOtpCode("");
      setTestResult(null);
    } catch (err: unknown) {
      console.error("Failed to disconnect:", err);
    } finally {
      setDisconnecting(false);
    }
  };

  // ── Resend OTP ──

  const handleResendOtp = () => {
    setOtpCode("");
    setVerifyError(null);
    handleLink();
  };

  // ── Loading State ──

  if (loading) {
    return (
      <div>
        <SettingsSection title="WhatsApp Connection" description="Connect your WhatsApp number">
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-brand-amber-light" />
            <span className="ml-3 text-sm text-[var(--color-text-muted)]">Loading connection status...</span>
          </div>
        </SettingsSection>
      </div>
    );
  }

  // ── Error State ──

  if (error && !status) {
    return (
      <div>
        <SettingsSection title="WhatsApp Connection">
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <X className="h-8 w-8 text-semantic-error mb-3" />
            <p className="text-sm text-[var(--color-text-secondary)] mb-3">{error}</p>
            <AnansiButton variant="secondary" size="sm" onClick={fetchStatus}>
              Retry
            </AnansiButton>
          </div>
        </SettingsSection>
      </div>
    );
  }

  const isConnected = status?.connected ?? false;

  // ── Render ──
  return (
    <div>
      {/* ── Connection Section ── */}
      <SettingsSection
        title="WhatsApp Connection"
        description={
          isConnected
            ? "Your WhatsApp is linked and ready"
            : "Link your WhatsApp number to chat with Anansi on the go"
        }
      >
        {isConnected && status ? (
          <div className="space-y-4">
            {/* Connected State */}
            <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-full bg-emerald-500/10 flex items-center justify-center">
                  <Check className="h-5 w-5 text-semantic-success-light" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-medium text-[var(--color-text-primary)]">
                      WhatsApp Connected
                    </p>
                    <ConnectionStatusBadge status={status.status} />
                  </div>
                  <p className="text-sm text-[var(--color-text-muted)]">
                    {status.phone_number}
                  </p>
                  {status.verified_at && (
                    <p className="text-xs text-[var(--color-text-disabled)] mt-0.5">
                      Connected {new Date(status.verified_at).toLocaleDateString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <AnansiButton
                    variant="secondary"
                    size="sm"
                    icon={<Send className="h-3.5 w-3.5" />}
                    onClick={handleSendTest}
                    disabled={sendingTest}
                    feedbackState={sendingTest ? "loading" : "idle"}
                  >
                    Test
                  </AnansiButton>
                </div>
              </div>

              {testResult && (
                <div className={cn(
                  "mt-3 p-3 rounded-lg text-sm",
                  testResult.startsWith("✅")
                    ? "bg-emerald-500/5 text-semantic-success-light border border-emerald-500/10"
                    : "bg-red-500/5 text-semantic-error border border-red-500/10",
                )}>
                  {testResult}
                </div>
              )}
            </div>

            {/* Disconnect */}
            <div className="border-t border-[var(--color-border-subtle)] pt-4">
              {showDisconnectConfirm ? (
                <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/10">
                  <p className="text-sm text-[var(--color-text-secondary)] mb-3">
                    Are you sure you want to disconnect WhatsApp? You&apos;ll need to
                    re-link to use WhatsApp features again.
                  </p>
                  <div className="flex gap-2">
                    <AnansiButton
                      variant="danger"
                      size="sm"
                      icon={<Trash2 className="h-3.5 w-3.5" />}
                      onClick={handleDisconnect}
                      disabled={disconnecting}
                      feedbackState={disconnecting ? "loading" : "idle"}
                    >
                      Disconnect
                    </AnansiButton>
                    <AnansiButton
                      variant="ghost"
                      size="sm"
                      onClick={() => setShowDisconnectConfirm(false)}
                    >
                      Cancel
                    </AnansiButton>
                  </div>
                </div>
              ) : (
                <AnansiButton
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowDisconnectConfirm(true)}
                >
                  Disconnect WhatsApp
                </AnansiButton>
              )}
            </div>
          </div>
        ) : (
          /* ── Not Connected — Link Flow ── */
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">
              Link your WhatsApp number to chat with Anansi on the go. Send voice notes,
              use quick commands like <code className="text-brand-amber-light text-xs">/briefing</code>,
              and get notifications directly on WhatsApp.
            </p>

            {/* Phone Input */}
            <Input
              label="Phone number (international format)"
              type="tel"
              placeholder="+2348012345678"
              value={phoneNumber}
              onChange={(e) => {
                setPhoneNumber(e.target.value);
                setLinkError(null);
              }}
              icon={<Smartphone className="h-4 w-4" />}
              disabled={linking}
            />

            {/* Error */}
            {linkError && (
              <p className="text-xs text-semantic-error flex items-center gap-1">
                <X className="h-3 w-3" /> {linkError}
              </p>
            )}

            {/* Link Button */}
            <AnansiButton
              variant="primary"
              icon={<MessageCircle className="h-4 w-4" />}
              onClick={handleLink}
              disabled={linking || !phoneNumber}
              feedbackState={linking ? "loading" : "idle"}
            >
              Send Verification Code
            </AnansiButton>

            {/* OTP Verification */}
            {showOtp && (
              <div className="mt-4 p-4 rounded-lg border border-brand-amber/20 bg-brand-amber/5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-[var(--color-text-primary)]">
                    Enter verification code
                  </p>
                  {otpTimer > 0 && (
                    <span className="text-xs text-[var(--color-text-muted)] font-mono">
                      {Math.floor(otpTimer / 60)}:{(otpTimer % 60).toString().padStart(2, "0")}
                    </span>
                  )}
                </div>

                <p className="text-xs text-[var(--color-text-muted)] mb-3">
                  A 6-digit code was sent to <strong>{phoneNumber}</strong>.
                  {otpTimer === 0 && " The code has expired. Request a new one."}
                </p>

                <OtpInput
                  length={6}
                  value={otpCode}
                  onChange={(val) => {
                    setOtpCode(val.replace(/\D/g, "").slice(0, 6));
                    setVerifyError(null);
                  }}
                  disabled={verifying || otpTimer === 0}
                />

                {verifyError && (
                  <p className="text-xs text-semantic-error flex items-center gap-1 mt-2">
                    <X className="h-3 w-3" /> {verifyError}
                  </p>
                )}

                <div className="flex gap-2 mt-3">
                  <AnansiButton
                    variant="primary"
                    size="sm"
                    onClick={handleVerify}
                    disabled={otpCode.length !== 6 || verifying || otpTimer === 0}
                    feedbackState={verifying ? "loading" : "idle"}
                  >
                    Verify
                  </AnansiButton>
                  {otpTimer === 0 ? (
                    <AnansiButton variant="secondary" size="sm" onClick={handleResendOtp} disabled={linking}>
                      Resend Code
                    </AnansiButton>
                  ) : (
                    <AnansiButton variant="ghost" size="sm" onClick={() => setShowOtp(false)}>
                      Cancel
                    </AnansiButton>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </SettingsSection>

      {/* ── Notification Preferences ── */}
      {isConnected && (
        <SettingsSection
          title="Notification Preferences"
          description="Choose which notifications you receive on WhatsApp"
        >
          <div className="divide-y divide-[var(--color-border-subtle)]/50">
            {NOTIFICATION_SETTINGS.map((setting) => (
              <Toggle
                key={setting.key}
                icon={setting.icon}
                label={setting.label}
                description={setting.description}
                enabled={notifSettings[setting.key] ?? true}
                onChange={(val) => handleToggleSetting(setting.key, val)}
              />
            ))}
          </div>

          {savingSettings && (
            <div className="flex items-center gap-2 pt-2 text-xs text-[var(--color-text-muted)]">
              <Loader2 className="h-3 w-3 animate-spin" />
              Saving...
            </div>
          )}
        </SettingsSection>
      )}

      {/* ── Features Info ── */}
      <SettingsSection title="WhatsApp Features" description="What you can do with WhatsApp">
        <div className="space-y-3 py-2">
          <FeatureRow
            icon={<MessageCircle className="h-4 w-4 text-brand-amber-light" />}
            title="AI Chat"
            description="Free-form conversation with your AI, connected to your Second Brain"
          />
          <FeatureRow
            icon={<Zap className="h-4 w-4 text-brand-amber-light" />}
            title="Quick Commands"
            description="/briefing, /tasks, /record, /summary, /graph, /brain, /help"
          />
          <FeatureRow
            icon={<div className="text-brand-amber-light text-xs font-bold">🎤</div>}
            title="Voice Notes"
            description="Send voice notes — I'll transcribe and process them"
          />
          <FeatureRow
            icon={<Bell className="h-4 w-4 text-brand-amber-light" />}
            title="Proactive Notifications"
            description="Briefings, agent results, alerts, and insights"
          />
        </div>
      </SettingsSection>
    </div>
  );
}

// ── Feature Row ──

function FeatureRow({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3 py-1">
      <div className="mt-0.5">{icon}</div>
      <div>
        <p className="text-sm font-medium text-[var(--color-text-primary)]">{title}</p>
        <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
      </div>
    </div>
  );
}
