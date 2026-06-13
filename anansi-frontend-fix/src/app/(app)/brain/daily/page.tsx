"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { useBrainStore } from "../../../../stores/brain";
import { GlassCard, GlassCardHeader, GlassCardTitle, GlassCardContent } from "../../../../components/ui/GlassCard";
import { AnansiButton } from "../../../../components/ui/AnansiButton";
import { Badge } from "../../../../components/ui/Badge";
import { BrainIcon } from "../../../../components/ui/BrainIcon";
import { api } from "../../../../lib/api";
import type { DailyNote, DailyNoteDecision } from "../../../../types";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  Download,
  CheckCircle2,
  Lightbulb,
  GitBranch,
  BarChart3,
  MessageSquare,
  Star,
  List,
  FileText,
} from "lucide-react";

export default function BrainDailyPage() {
  const { dailyNote, isLoadingDailyNote, loadDailyNote } = useBrainStore();
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [notes, setNotes] = useState<DailyNote[]>([]);
  const [activeNote, setActiveNote] = useState<DailyNote | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isFinalizing, setIsFinalizing] = useState(false);

  // Load notes on mount
  useEffect(() => {
    loadDailyNote();
    loadHistory();
  }, [loadDailyNote]);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    try {
      // Load last 30 days of notes
      const history: DailyNote[] = [];
      for (let i = 0; i < 30; i++) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        const dateStr = date.toISOString().split("T")[0];
        try {
          const resp = await api.get<{ note: DailyNote }>(`/api/v1/brain/daily/${dateStr}`);
          history.push(resp.note);
        } catch {
          // No note for this date
        }
      }
      setNotes(history);
    } catch (err) {
      console.error("Failed to load history:", err);
    }
    setIsLoadingHistory(false);
  };

  const selectedDateStr = selectedDate.toISOString().split("T")[0];
  const todayStr = new Date().toISOString().split("T")[0];
  const isToday = selectedDateStr === todayStr;

  const activeNoteForDate = useMemo(
    () => activeNote || notes.find((n) => n.noteDate === selectedDateStr) || dailyNote,
    [activeNote, notes, dailyNote, selectedDateStr],
  );

  // Generate daily note
  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      const resp = await api.post<{ note: DailyNote }>("/api/v1/brain/daily/generate", {
        date: selectedDateStr,
      });
      setActiveNote(resp.note);
    } catch (err) {
      console.error("Failed to generate:", err);
    }
    setIsGenerating(false);
  };

  // Finalize
  const handleFinalize = async () => {
    if (!isToday) return;
    setIsFinalizing(true);
    try {
      await handleGenerate();
      if (activeNoteForDate && !activeNoteForDate.isFinalized) {
        // Re-fetch to get finalized state
        loadDailyNote();
      }
    } catch (err) {
      console.error("Failed to finalize:", err);
    }
    setIsFinalizing(false);
  };

  // Navigate dates
  const goToDate = (offset: number) => {
    const newDate = new Date(selectedDate);
    newDate.setDate(newDate.getDate() + offset);
    setSelectedDate(newDate);
    setActiveNote(null);
  };

  // Calendar grid
  const calendarDays = useMemo(() => {
    const year = selectedDate.getFullYear();
    const month = selectedDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const days: (number | null)[] = [];

    // Fill in leading empty days
    for (let i = 0; i < firstDay.getDay(); i++) {
      days.push(null);
    }

    // Fill in the days
    for (let i = 1; i <= lastDay.getDate(); i++) {
      days.push(i);
    }

    return days;
  }, [selectedDate]);

  const notesByDate = useMemo(() => {
    const map: Record<string, DailyNote> = {};
    notes.forEach((n) => {
      map[n.noteDate] = n;
    });
    if (dailyNote) map[dailyNote.noteDate] = dailyNote;
    return map;
  }, [notes, dailyNote]);

  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Check if a date has a note
  const hasNote = (day: number) => {
    const dateStr = `${selectedDate.getFullYear()}-${String(selectedDate.getMonth() + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    return !!notesByDate[dateStr];
  };

  const isSelectedDay = (day: number) => {
    return selectedDate.getDate() === day;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-heading font-bold text-[var(--color-text-primary)] flex items-center gap-2">
            <Calendar className="h-6 w-6 text-brand-amber-light" />
            Daily Notes
          </h1>
          <p className="text-sm text-[var(--color-text-muted)] mt-1">
            Your temporal anchor — highlights, decisions, and connections for each day
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-[300px_1fr] gap-6">
        {/* Calendar sidebar */}
        <div className="space-y-4">
          <GlassCard variant="base" padding="md">
            {/* Month nav */}
            <div className="flex items-center justify-between mb-4">
              <button onClick={() => goToDate(-30)} className="p-1 rounded hover:bg-white/10 transition-colors">
                <ChevronLeft className="h-4 w-4 text-[var(--color-text-muted)]" />
              </button>
              <span className="text-sm font-semibold text-[var(--color-text-primary)]">
                {monthNames[selectedDate.getMonth()]} {selectedDate.getFullYear()}
              </span>
              <button onClick={() => goToDate(30)} className="p-1 rounded hover:bg-white/10 transition-colors">
                <ChevronRight className="h-4 w-4 text-[var(--color-text-muted)]" />
              </button>
            </div>

            {/* Day headers */}
            <div className="grid grid-cols-7 gap-1 mb-2">
              {dayNames.map((d) => (
                <div key={d} className="text-center text-xs text-[var(--color-text-muted)] font-medium">
                  {d[0]}
                </div>
              ))}
            </div>

            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
              {calendarDays.map((day, i) => (
                <div key={i} className="aspect-square">
                  {day !== null ? (
                    <button
                      onClick={() => {
                        const newDate = new Date(selectedDate);
                        newDate.setDate(day);
                        setSelectedDate(newDate);
                        setActiveNote(null);
                      }}
                      className={`w-full h-full rounded-lg text-xs flex items-center justify-center transition-colors relative ${
                        isSelectedDay(day)
                          ? "bg-brand-amber/20 text-brand-amber-light font-semibold"
                          : hasNote(day)
                            ? "bg-brand-amber/10 text-[var(--color-text-primary)] hover:bg-white/10"
                            : "text-[var(--color-text-muted)] hover:bg-white/5"
                      }`}
                    >
                      {day}
                      {hasNote(day) && !isSelectedDay(day) && (
                        <span className="absolute bottom-0.5 w-1 h-1 rounded-full bg-brand-amber/60" />
                      )}
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Today's quick link */}
          <GlassCard variant="interactive" glow="amber" padding="sm">
            <button
              onClick={() => setSelectedDate(new Date())}
              className="w-full text-left flex items-center gap-2 text-sm text-[var(--color-text-primary)]"
            >
              <Star className="h-4 w-4 text-brand-amber-light" />
              Today
            </button>
          </GlassCard>
        </div>

        {/* Daily note content */}
        <div className="space-y-4">
          {/* Date header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-heading font-bold text-[var(--color-text-primary)]">
                {isToday ? "Today" : selectedDate.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" })}
              </h2>
              {activeNoteForDate?.isFinalized && (
                <Badge variant="success" size="sm" pill>
                  <CheckCircle2 className="h-3 w-3" /> Finalized
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2">
              <AnansiButton
                variant="secondary"
                size="sm"
                onClick={handleGenerate}
                feedbackState={isGenerating ? "loading" : "idle"}
              >
                <Sparkles className="h-4 w-4" />
                Generate
              </AnansiButton>
              {isToday && (
                <AnansiButton
                  variant="primary"
                  size="sm"
                  onClick={handleFinalize}
                  disabled={activeNoteForDate?.isFinalized}
                  feedbackState={isFinalizing ? "loading" : "idle"}
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Finalize
                </AnansiButton>
              )}
            </div>
          </div>

          {isLoadingHistory || isLoadingDailyNote ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-48 rounded-lg bg-white/5" />
              <div className="h-32 rounded-lg bg-white/5" />
            </div>
          ) : activeNoteForDate ? (
            <div className="space-y-4">
              {/* Metrics */}
              <GlassCard variant="base" padding="md">
                <GlassCardHeader>
                  <GlassCardTitle>
                    <div className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-brand-teal-light" />
                      Metrics
                    </div>
                  </GlassCardTitle>
                </GlassCardHeader>
                <GlassCardContent>
                  <div className="grid grid-cols-5 gap-4">
                    {Object.entries(
                      (activeNoteForDate as DailyNote).metrics || {},
                    ).map(([key, value]) => (
                      <div key={key} className="text-center">
                        <p className="text-xl font-bold text-[var(--color-text-primary)]">
                          {value as number}
                        </p>
                        <p className="text-xs text-[var(--color-text-muted)]">
                          {key.replace(/_/g, " ").replace(/([A-Z])/g, " $1").trim()}
                        </p>
                      </div>
                    ))}
                  </div>
                </GlassCardContent>
              </GlassCard>

              {/* Highlights */}
              <GlassCard variant="base" padding="md">
                <GlassCardHeader>
                  <GlassCardTitle>
                    <div className="flex items-center gap-2">
                      <Star className="h-4 w-4 text-brand-amber-light" />
                      Highlights
                    </div>
                  </GlassCardTitle>
                  <Badge variant="brand" size="sm" pill>
                    {(activeNoteForDate as DailyNote).highlights?.length || 0}
                  </Badge>
                </GlassCardHeader>
                <GlassCardContent>
                  {(activeNoteForDate as DailyNote).highlights?.length > 0 ? (
                    <ul className="space-y-2">
                      {(activeNoteForDate as DailyNote).highlights.map((h, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-[var(--color-text-secondary)]">
                          <span className="text-brand-amber-light mt-0.5">•</span>
                          {h}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-[var(--color-text-muted)] italic">No highlights yet</p>
                  )}
                </GlassCardContent>
              </GlassCard>

              {/* Decisions */}
              <GlassCard variant="base" padding="md">
                <GlassCardHeader>
                  <GlassCardTitle>
                    <div className="flex items-center gap-2">
                      <Lightbulb className="h-4 w-4 text-brand-violet-light" />
                      Decisions
                    </div>
                  </GlassCardTitle>
                </GlassCardHeader>
                <GlassCardContent>
                  {(activeNoteForDate as DailyNote).decisions?.length > 0 ? (
                    <ul className="space-y-2">
                      {(activeNoteForDate as DailyNote).decisions.map((d: DailyNoteDecision, i: number) => (
                        <li key={i} className="flex items-start gap-2 text-sm">
                          <CheckCircle2 className={`h-4 w-4 mt-0.5 ${d.approved ? "text-semantic-success" : "text-[var(--color-text-muted)]"}`} />
                          <span className="text-[var(--color-text-secondary)]">{d.description}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-[var(--color-text-muted)] italic">No decisions recorded</p>
                  )}
                </GlassCardContent>
              </GlassCard>

              {/* Connections */}
              <GlassCard variant="base" padding="md">
                <GlassCardHeader>
                  <GlassCardTitle>
                    <div className="flex items-center gap-2">
                      <GitBranch className="h-4 w-4 text-brand-teal-light" />
                      Connections
                    </div>
                  </GlassCardTitle>
                </GlassCardHeader>
                <GlassCardContent>
                  {(activeNoteForDate as DailyNote).connectionsMade?.length > 0 ? (
                    <ul className="space-y-2">
                      {(activeNoteForDate as DailyNote).connectionsMade.map((c: any, i: number) => (
                        <li key={i} className="flex items-center gap-2 text-sm text-[var(--color-text-secondary)]">
                          <span className="text-brand-teal-light">↔</span>
                          {c.fromNode} → {c.toNode}
                          <Badge variant="brand" size="sm" pill>
                            {c.linkType?.replace(/_/g, " ")}
                          </Badge>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-[var(--color-text-muted)] italic">No new connections</p>
                  )}
                </GlassCardContent>
              </GlassCard>

              {/* AI Reflection */}
              {(activeNoteForDate as DailyNote).aiReflection && (
                <GlassCard variant="elevated" glow="amber" padding="md">
                  <GlassCardHeader>
                    <GlassCardTitle>
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-brand-amber-light" />
                        AI Reflection
                      </div>
                    </GlassCardTitle>
                  </GlassCardHeader>
                  <GlassCardContent>
                    <p className="text-sm text-[var(--color-text-secondary)] italic leading-relaxed">
                      {(activeNoteForDate as DailyNote).aiReflection}
                    </p>
                  </GlassCardContent>
                </GlassCard>
              )}
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 text-[var(--color-text-muted)] mx-auto mb-3" />
              <p className="text-[var(--color-text-muted)]">No daily note for this date</p>
              <AnansiButton
                variant="secondary"
                size="sm"
                onClick={handleGenerate}
                className="mt-3"
                feedbackState={isGenerating ? "loading" : "idle"}
              >
                <Sparkles className="h-4 w-4" />
                Generate Note
              </AnansiButton>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
