"use client";

import { useState } from "react";
import Link from "next/link";
import { BrainIcon } from "../../../components/ui/BrainIcon";
import { GlassCard } from "../../../components/ui/GlassCard";
import { Input } from "../../../components/ui/Input";
import { AnansiButton } from "../../../components/ui/AnansiButton";
import { Mail, ArrowLeft, CheckCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Stub — will wire to auth API later
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4 py-12">
        <div className="relative z-10 w-full max-w-sm">
          <GlassCard variant="elevated" padding="lg" className="text-center">
            <div className="flex justify-center mb-4">
              <CheckCircle className="h-12 w-12 text-semantic-success-light" />
            </div>
            <h1 className="text-xl font-heading font-bold text-[var(--color-text-primary)] mb-2">
              Check your email
            </h1>
            <p className="text-sm text-[var(--color-text-muted)] mb-6">
              We&apos;ve sent a password reset link to{" "}
              <strong className="text-[var(--color-text-secondary)]">{email}</strong>
            </p>
            <Link href="/login">
              <AnansiButton variant="secondary" fullWidth icon={<ArrowLeft className="h-4 w-4" />}>
                Back to sign in
              </AnansiButton>
            </Link>
          </GlassCard>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/3 right-1/3 w-64 h-64 bg-brand-amber/5 rounded-full blur-[96px]" />
      </div>

      <div className="relative z-10 w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <BrainIcon size={40} active={false} />
          </div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">Reset your password</h1>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">
            Enter your email and we&apos;ll send you a reset link
          </p>
        </div>

        <GlassCard variant="elevated" padding="lg">
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              icon={<Mail className="h-4 w-4" />}
              required
            />

            <AnansiButton type="submit" variant="primary" fullWidth size="lg">
              Send Reset Link
            </AnansiButton>
          </form>

          <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
            Remember your password?{" "}
            <Link href="/login" className="text-brand-amber-light hover:text-brand-amber font-medium transition-colors">
              Sign in
            </Link>
          </p>
        </GlassCard>
      </div>
    </div>
  );
}
