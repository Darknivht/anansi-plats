/**
 * New Agent Canvas Page — Same workshop canvas but for creating new agents.
 *
 * "/agents/new/canvas" — The canvas pre-populated with a template or blank.
 * There's no agent ID yet — it gets created on first save.
 */

"use client";

import dynamic from "next/dynamic";

// Dynamically import the workshop to avoid SSR issues with React Flow
const WorkshopPage = dynamic(
  () => import("../../[id]/page"),
  { ssr: false }
);

export default function NewAgentCanvasPage() {
  return <WorkshopPage />;
}
