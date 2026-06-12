"use client";

import { useState } from "react";
import { GlassCard, GlassCardHeader, GlassCardTitle } from "@/components/ui/GlassCard";
import { Input } from "@/components/ui/Input";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import {
  User,
  Shield,
  Bell,
  Brain,
  CreditCard,
  MessageCircle,
  Download,
  ChevronRight,
  Key,
  Smartphone,
  Globe,
  Clock,
  Palette,
  ToggleLeft,
  Check,
  X,
  ExternalLink,
} from "lucide-react";
import WhatsAppSettingsComponent from "@/app/(app)/settings/components/WhatsAppSettings";

type SettingsTab =
  | "profile"
  | "security"
  | "notifications"
  | "brain"
  | "billing"
  | "whatsapp"
  | "data";

interface TabDef {
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
}

const tabs: TabDef[] = [
  { id: "profile", label: "Profile", icon: <User className="h-4 w-4" /> },
  { id: "security", label: "Security", icon: <Shield className="h-4 w-4" /> },
  { id: "notifications", label: "Notifications", icon: <Bell className="h-4 w-4" /> },
  { id: "brain", label: "Brain Settings", icon: <Brain className="h-4 w-4" /> },
  { id: "billing", label: "Billing", icon: <CreditCard className="h-4 w-4" /> },
  { id: "whatsapp", label: "WhatsApp", icon: <MessageCircle className="h-4 w-4" /> },
  { id: "data", label: "Data & Privacy", icon: <Download className="h-4 w-4" /> },
];

// ── Toggle Switch component ──

function Toggle({ enabled, onChange, label }: { enabled: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        onClick={() => onChange(!enabled)}
        className={cn(
          "relative inline-flex h-5 w-9 items-center rounded-full transition-colors duration-200 ease-anansi",
          enabled ? "bg-brand-amber-light" : "bg-[var(--color-border-subtle)]",
        )}
      >
        <span
          className={cn(
            "inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform duration-200 ease-anansi",
            enabled ? "translate-x-4.5" : "translate-x-1",
          )}
        />
      </button>
      <span className="text-sm text-[var(--color-text-secondary)]">{label}</span>
    </label>
  );
}

// ── Settings Card wrapper ──

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
      <div className="space-y-4">{children}</div>
    </GlassCard>
  );
}

function SettingsRow({
  icon,
  label,
  description,
  children,
}: {
  icon?: React.ReactNode;
  label: string;
  description?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex items-center gap-3">
        {icon && <span className="text-[var(--color-text-muted)]">{icon}</span>}
        <div>
          <p className="text-sm text-[var(--color-text-primary)]">{label}</p>
          {description && (
            <p className="text-xs text-[var(--color-text-muted)]">{description}</p>
          )}
        </div>
      </div>
      {children && <div className="flex items-center gap-2">{children}</div>}
    </div>
  );
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("profile");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">Settings</h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Manage your account, security, and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Tab Navigation */}
        <nav className="lg:w-56 shrink-0" aria-label="Settings tabs">
          <div className="flex lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap",
                  "transition-all duration-200 ease-anansi",
                  activeTab === tab.id
                    ? "bg-amber-500/10 text-brand-amber-light border border-amber-500/20"
                    : "text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] hover:bg-white/5 border border-transparent",
                )}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.id}
              >
                {tab.icon}
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </nav>

        {/* Tab Content */}
        <div className="flex-1 min-w-0">
          {activeTab === "profile" && <ProfileSettings />}
          {activeTab === "security" && <SecuritySettings />}
          {activeTab === "notifications" && <NotificationSettings />}
          {activeTab === "brain" && <BrainSettings />}
          {activeTab === "billing" && <BillingSettings />}
          {activeTab === "whatsapp" && <WhatsAppSettings />}
          {activeTab === "data" && <DataPrivacySettings />}
        </div>
      </div>
    </div>
  );
}

// ── Profile ──

function ProfileSettings() {
  return (
    <div>
      <SettingsSection title="Profile" description="Update your personal information">
        <Input label="Display name" defaultValue="Ada" placeholder="Your name" />
        <Input label="Email" type="email" defaultValue="ada@example.com" placeholder="you@example.com" />
        <Input label="Username" defaultValue="@ada" placeholder="@username" />
        <div className="grid grid-cols-2 gap-4">
          <Input label="Timezone" defaultValue="Africa/Lagos" />
          <Input label="Language" defaultValue="English" />
        </div>
        <div className="flex items-center gap-4">
          <div className="h-16 w-16 rounded-full bg-gradient-to-br from-brand-amber to-brand-amber-light flex items-center justify-center text-white text-xl font-bold">
            A
          </div>
          <AnansiButton variant="secondary" size="sm">
            Change avatar
          </AnansiButton>
        </div>
        <div className="pt-2">
          <AnansiButton variant="primary">Save changes</AnansiButton>
        </div>
      </SettingsSection>
    </div>
  );
}

// ── Security ──

function SecuritySettings() {
  return (
    <div>
      <SettingsSection title="Password" description="Change your password">
        <Input label="Current password" type="password" placeholder="Enter current password" />
        <Input label="New password" type="password" placeholder="Enter new password" />
        <Input label="Confirm new password" type="password" placeholder="Confirm new password" />
        <AnansiButton variant="primary">Update password</AnansiButton>
      </SettingsSection>

      <SettingsSection title="Two-Factor Authentication" description="Add an extra layer of security">
        <SettingsRow
          icon={<Key className="h-4 w-4" />}
          label="Authenticator app"
          description="Use an app like Google Authenticator or Authy"
        >
          <Badge variant="warning" size="sm">Not enabled</Badge>
          <AnansiButton variant="secondary" size="sm">Enable</AnansiButton>
        </SettingsRow>
      </SettingsSection>

      <SettingsSection title="Active Sessions" description="Devices currently signed into your account">
        {[
          { device: "Chrome on macOS", location: "Lagos, Nigeria", active: true },
          { device: "Safari on iPhone", location: "Lagos, Nigeria", active: true },
        ].map((session) => (
          <div key={session.device} className="flex items-center justify-between py-2">
            <div className="flex items-center gap-3">
              <Smartphone className="h-4 w-4 text-[var(--color-text-muted)]" />
              <div>
                <p className="text-sm text-[var(--color-text-primary)]">{session.device}</p>
                <p className="text-xs text-[var(--color-text-muted)]">{session.location}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {session.active && <span className="h-2 w-2 rounded-full bg-semantic-success-light" />}
              <AnansiButton variant="ghost" size="sm">Revoke</AnansiButton>
            </div>
          </div>
        ))}
      </SettingsSection>
    </div>
  );
}

// ── Notifications ──

function NotificationSettings() {
  const [notifStates, setNotifStates] = useState({
    emailAlerts: true,
    agentCompleted: true,
    brainInsights: true,
    marketingEmails: false,
    morningBriefing: true,
    whatsappAlerts: true,
  });

  return (
    <div>
      <SettingsSection title="Notification Preferences">
        <Toggle
          enabled={notifStates.morningBriefing}
          onChange={(v) => setNotifStates((s) => ({ ...s, morningBriefing: v }))}
          label="Morning Briefing"
        />
        <Toggle
          enabled={notifStates.emailAlerts}
          onChange={(v) => setNotifStates((s) => ({ ...s, emailAlerts: v }))}
          label="Email alerts"
        />
        <Toggle
          enabled={notifStates.agentCompleted}
          onChange={(v) => setNotifStates((s) => ({ ...s, agentCompleted: v }))}
          label="Agent completed notifications"
        />
        <Toggle
          enabled={notifStates.brainInsights}
          onChange={(v) => setNotifStates((s) => ({ ...s, brainInsights: v }))}
          label="Brain insights & suggestions"
        />
        <Toggle
          enabled={notifStates.whatsappAlerts}
          onChange={(v) => setNotifStates((s) => ({ ...s, whatsappAlerts: v }))}
          label="WhatsApp notifications"
        />
        <Toggle
          enabled={notifStates.marketingEmails}
          onChange={(v) => setNotifStates((s) => ({ ...s, marketingEmails: v }))}
          label="Marketing emails"
        />
      </SettingsSection>
    </div>
  );
}

// ── Brain Settings ──

function BrainSettings() {
  const [brainSettings, setBrainSettings] = useState({
    autoLinking: true,
    dailyNotes: true,
    spacedRepetition: true,
    progressiveSummarization: true,
  });

  return (
    <div>
      <SettingsSection title="Brain Settings" description="Configure how your Second Brain works">
        <Toggle
          enabled={brainSettings.autoLinking}
          onChange={(v) => setBrainSettings((s) => ({ ...s, autoLinking: v }))}
          label="Auto-linking — automatically suggest connections between memories"
        />
        <Toggle
          enabled={brainSettings.dailyNotes}
          onChange={(v) => setBrainSettings((s) => ({ ...s, dailyNotes: v }))}
          label="Daily Notes — automatically generate daily summaries"
        />
        <Toggle
          enabled={brainSettings.spacedRepetition}
          onChange={(v) => setBrainSettings((s) => ({ ...s, spacedRepetition: v }))}
          label="Spaced Repetition — schedule periodic memory reviews"
        />
        <Toggle
          enabled={brainSettings.progressiveSummarization}
          onChange={(v) => setBrainSettings((s) => ({ ...s, progressiveSummarization: v }))}
          label="Progressive Summarization — distill memories into layers"
        />
      </SettingsSection>

      <SettingsSection title="Review Schedule" description="Configure when you review your memories">
        <Input label="Daily review limit" type="number" defaultValue={5} />
        <Input label="Review time" type="time" defaultValue="09:00" />
      </SettingsSection>

      <SettingsSection title="Export" description="Export your Second Brain">
        <div className="flex items-center gap-3">
          <AnansiButton variant="secondary" icon={<Download className="h-4 w-4" />}>
            Export as JSON
          </AnansiButton>
          <AnansiButton variant="secondary" icon={<Download className="h-4 w-4" />}>
            Export as Obsidian Vault
          </AnansiButton>
        </div>
      </SettingsSection>
    </div>
  );
}

// ── Billing ──

function BillingSettings() {
  const plan = {
    name: "Pro",
    price: "$19",
    period: "month",
    status: "active",
  };

  return (
    <div>
      <SettingsSection title="Current Plan" description="Your subscription details">
        <div className="flex items-center justify-between p-4 rounded-lg bg-amber-500/5 border border-amber-500/10">
          <div>
            <p className="text-lg font-heading font-bold text-[var(--color-text-primary)]">
              {plan.name} Plan
            </p>
            <p className="text-sm text-[var(--color-text-muted)]">
              {plan.price}/{plan.period} • <Badge variant="success" size="sm">Active</Badge>
            </p>
          </div>
          <div className="flex gap-2">
            <AnansiButton variant="secondary" size="sm">Change plan</AnansiButton>
            <AnansiButton variant="ghost" size="sm">Cancel</AnansiButton>
          </div>
        </div>
      </SettingsSection>

      <SettingsSection title="Payment Method" description="Manage your payment details">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <CreditCard className="h-5 w-5 text-[var(--color-text-muted)]" />
            <div>
              <p className="text-sm text-[var(--color-text-primary)]">Visa ending in 4242</p>
              <p className="text-xs text-[var(--color-text-muted)]">Expires 12/27</p>
            </div>
          </div>
          <AnansiButton variant="secondary" size="sm">Update</AnansiButton>
        </div>
      </SettingsSection>

      <SettingsSection title="Invoices" description="View and download past invoices">
        {["June 2026", "May 2026", "April 2026"].map((inv) => (
          <div key={inv} className="flex items-center justify-between py-2">
            <span className="text-sm text-[var(--color-text-primary)]">{inv}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs text-[var(--color-text-muted)]">$19.00</span>
              <button className="text-xs text-brand-amber-light hover:text-brand-amber transition-colors" type="button">
                Download
              </button>
            </div>
          </div>
        ))}
      </SettingsSection>
    </div>
  );
}

// ── WhatsApp ──

function WhatsAppSettings() {
  return <WhatsAppSettingsComponent />;
}

// ── Data & Privacy ──

function DataPrivacySettings() {
  return (
    <div>
      <SettingsSection title="Data Export" description="Download all your data">
        <p className="text-sm text-[var(--color-text-secondary)]">
          You can export all your data including memories, conversations, agents, and settings.
        </p>
        <div className="flex flex-wrap gap-3">
          <AnansiButton variant="secondary" icon={<Download className="h-4 w-4" />}>
            Export All Data
          </AnansiButton>
          <AnansiButton variant="secondary" icon={<Download className="h-4 w-4" />}>
            Export Memories Only
          </AnansiButton>
          <AnansiButton variant="secondary" icon={<Download className="h-4 w-4" />}>
            Export Conversations
          </AnansiButton>
        </div>
      </SettingsSection>

      <SettingsSection title="Privacy" description="Manage your privacy settings">
        <Toggle enabled={true} onChange={() => {}} label="Allow AI to learn from my conversations" />
        <Toggle enabled={true} onChange={() => {}} label="Share anonymous usage data to improve Anansi" />
        <Toggle enabled={false} onChange={() => {}} label="Allow AI to scan my emails for memory" />
      </SettingsSection>

      <SettingsSection title="Delete Account" description="Permanently delete your account and all data">
        <p className="text-sm text-[var(--color-text-secondary)] mb-3">
          This action is irreversible. All your memories, agents, integrations, and settings will be permanently deleted.
        </p>
        <AnansiButton variant="danger">
          Delete my account
        </AnansiButton>
      </SettingsSection>
    </div>
  );
}
