"use client";

import { useState } from "react";
import Link from "next/link";
import { BrainIcon } from "@/components/ui/BrainIcon";
import { GlassCard } from "@/components/ui/GlassCard";
import { Input } from "@/components/ui/Input";
import { AnansiButton } from "@/components/ui/AnansiButton";
import { Eye, EyeOff, Mail, Lock, Github } from "lucide-react";

export default function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Stub — will wire to auth API later
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      {/* Ambient background */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 right-1/4 w-64 h-64 bg-brand-amber/5 rounded-full blur-[96px]" />
        <div className="absolute bottom-1/3 left-1/4 w-72 h-72 bg-brand-violet/5 rounded-full blur-[96px]" />
      </div>

      <div className="relative z-10 w-full max-w-sm">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <BrainIcon size={40} active glow="amber" />
          </div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)]">Welcome back</h1>
          <p className="mt-2 text-sm text-[var(--color-text-muted)]">Sign in to your Second Brain</p>
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

            <div className="relative">
              <Input
                label="Password"
                type={showPassword ? "text" : "password"}
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                icon={<Lock className="h-4 w-4" />}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 bottom-[10px] text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] transition-colors"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>

            <div className="flex items-center justify-end">
              <Link
                href="/forgot-password"
                className="text-xs text-brand-amber-light hover:text-brand-amber transition-colors"
              >
                Forgot password?
              </Link>
            </div>

            <AnansiButton type="submit" variant="primary" fullWidth size="lg">
              Sign In
            </AnansiButton>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[var(--color-border-subtle)]" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="px-2 bg-[var(--color-surface-card)] text-[var(--color-text-muted)]">or continue with</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-amber-500/30 hover:text-[var(--color-text-primary)] transition-all duration-200 ease-anansi"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </button>
            <button
              type="button"
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-[var(--color-text-secondary)] border border-[var(--color-border-subtle)] hover:border-amber-500/30 hover:text-[var(--color-text-primary)] transition-all duration-200 ease-anansi"
            >
              <Github className="h-5 w-5" />
              GitHub
            </button>
          </div>

          <p className="mt-6 text-center text-sm text-[var(--color-text-muted)]">
            Don&apos;t have an account?{" "}
            <Link href="/signup" className="text-brand-amber-light hover:text-brand-amber font-medium transition-colors">
              Sign up
            </Link>
          </p>
        </GlassCard>
      </div>
    </div>
  );
}
