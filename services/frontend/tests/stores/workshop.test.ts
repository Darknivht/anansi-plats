import { describe, it, expect, beforeEach } from 'vitest';
import { useWorkshopStore } from '@/stores/workshop';

describe('Workshop Store', () => {
  beforeEach(() => {
    useWorkshopStore.setState({
      nodes: [],
      edges: [],
      selectedNodeId: null,
      isDirty: false,
      testMode: false,
      agentId: null,
      agentName: '',
      agentDescription: '',
      agentVersion: 1,
      isSaving: false,
      lastSavedAt: null,
      history: [],
      historyIndex: -1,
      maxHistory: 50,
    });
  });

  it('starts with empty canvas', () => {
    const state = useWorkshopStore.getState();
    expect(state.nodes).toHaveLength(0);
    expect(state.edges).toHaveLength(0);
    expect(state.isDirty).toBe(false);
    expect(state.agentId).toBeNull();
  });

  it('adds a node to the canvas', () => {
    const nodeId = useWorkshopStore.getState().addNode('ai', 'ai.conversation');
    expect(nodeId).toBeDefined();
    const state = useWorkshopStore.getState();
    expect(state.nodes).toHaveLength(1);
    expect(state.nodes[0].data.type).toBe('ai');
    expect(state.nodes[0].data.subtype).toBe('ai.conversation');
    expect(state.isDirty).toBe(true);
  });

  it('adds a node at a specific position', () => {
    const nodeId = useWorkshopStore.getState().addNode('trigger', 'trigger.schedule', { x: 100, y: 200 });
    const node = useWorkshopStore.getState().nodes.find(n => n.id === nodeId);
    expect(node).toBeDefined();
    expect(node!.position).toEqual({ x: 100, y: 200 });
  });

  it('removes a node', () => {
    const nodeId = useWorkshopStore.getState().addNode('action', 'action.send_email');
    expect(useWorkshopStore.getState().nodes).toHaveLength(1);
    useWorkshopStore.getState().removeNode(nodeId);
    expect(useWorkshopStore.getState().nodes).toHaveLength(0);
  });

  it('removes selected node', () => {
    const nodeId = useWorkshopStore.getState().addNode('logic', 'logic.condition');
    useWorkshopStore.getState().selectNode(nodeId);
    useWorkshopStore.getState().removeSelectedNode();
    expect(useWorkshopStore.getState().nodes).toHaveLength(0);
    expect(useWorkshopStore.getState().selectedNodeId).toBeNull();
  });

  it('selects a node', () => {
    const nodeId = useWorkshopStore.getState().addNode('ai', 'ai.generate');
    useWorkshopStore.getState().selectNode(nodeId);
    expect(useWorkshopStore.getState().selectedNodeId).toBe(nodeId);

    useWorkshopStore.getState().selectNode(null);
    expect(useWorkshopStore.getState().selectedNodeId).toBeNull();
  });

  it('updates node config', () => {
    const nodeId = useWorkshopStore.getState().addNode('ai', 'ai.conversation');
    useWorkshopStore.getState().updateNodeConfig(nodeId, { model: 'claude-opus-4', temperature: 0.5 });
    const node = useWorkshopStore.getState().nodes.find(n => n.id === nodeId);
    expect(node!.data.config.model).toBe('claude-opus-4');
    expect(node!.data.config.temperature).toBe(0.5);
  });

  it('creates an edge between nodes', () => {
    const node1Id = useWorkshopStore.getState().addNode('trigger', 'trigger.schedule');
    const node2Id = useWorkshopStore.getState().addNode('ai', 'ai.conversation');

    const state = useWorkshopStore.getState();
    // Simulate reactflow onConnect
    state.onConnect({ source: node1Id, target: node2Id, sourceHandle: null, targetHandle: null });
    expect(useWorkshopStore.getState().edges).toHaveLength(1);
  });

  it('toggles test mode', () => {
    expect(useWorkshopStore.getState().testMode).toBe(false);
    useWorkshopStore.getState().setTestMode(true);
    expect(useWorkshopStore.getState().testMode).toBe(true);
    useWorkshopStore.getState().setTestMode(false);
    expect(useWorkshopStore.getState().testMode).toBe(false);
  });

  it('sets agent metadata', () => {
    useWorkshopStore.getState().setAgentMeta({ name: 'My Agent', description: 'An agent', version: 2 });
    expect(useWorkshopStore.getState().agentName).toBe('My Agent');
    expect(useWorkshopStore.getState().agentDescription).toBe('An agent');
    expect(useWorkshopStore.getState().agentVersion).toBe(2);
  });

  it('marks clean and dirty states', () => {
    useWorkshopStore.getState().markClean();
    expect(useWorkshopStore.getState().isDirty).toBe(false);
  });

  it('supports undo/redo', () => {
    const state = useWorkshopStore.getState();
    expect(state.canUndo()).toBe(false);
    expect(state.canRedo()).toBe(false);

    state.addNode('ai', 'ai.conversation');
    expect(useWorkshopStore.getState().canUndo()).toBe(true);

    useWorkshopStore.getState().undo();
    expect(useWorkshopStore.getState().nodes).toHaveLength(0);

    useWorkshopStore.getState().redo();
    expect(useWorkshopStore.getState().nodes).toHaveLength(1);
  });

  it('serializes to agent definition', () => {
    useWorkshopStore.getState().setAgentMeta({ name: 'Serialized Agent' });
    useWorkshopStore.getState().addNode('trigger', 'trigger.webhook');
    const def = useWorkshopStore.getState().toAgentDefinition();
    expect(def).toBeDefined();
    expect(def.name).toBe('Serialized Agent');
  });

  it('sets saving state', () => {
    useWorkshopStore.getState().setIsSaving(true);
    expect(useWorkshopStore.getState().isSaving).toBe(true);
    useWorkshopStore.getState().setIsSaving(false);
    expect(useWorkshopStore.getState().isSaving).toBe(false);
  });
});
