/**
 * Create Agent Page — Template selection with blank canvas and pre-built templates.
 *
 * "/agents/new"
 * Shows template grid, clicking a template navigates to the canvas with data pre-loaded.
 */

"use client";

import { useRouter } from "next/navigation";
import { TemplateSelector } from "../../../../components/workshop/TemplateSelector";
import type { AgentTemplate } from "../../../../components/workshop/TemplateSelector";
import { useWorkshopStore } from "../../../../stores/workshop";

export default function NewAgentPage() {
  const router = useRouter();
  const { fromAgentDefinition, setAgentMeta } = useWorkshopStore();

  const handleSelect = (template: AgentTemplate) => {
    // Load template into workshop store
    fromAgentDefinition(template.definition);

    // Set agent metadata
    if (template.id === "blank") {
      setAgentMeta({ name: "Untitled Agent", description: "" });
    } else {
      setAgentMeta({ name: template.name, description: template.description });
    }

    // Navigate to canvas (new agent creation flow)
    router.push("/agents/new/canvas");
  };

  return (
    <div className="min-h-screen py-8">
      <TemplateSelector onSelect={handleSelect} />
    </div>
  );
}
