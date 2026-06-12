import { describe, it, expect, beforeEach } from 'vitest';
import { useBrainStore } from '@/stores/brain';

describe('Brain Store', () => {
  beforeEach(() => {
    useBrainStore.setState({
      nodes: [],
      edges: [],
      selectedNodeId: null,
      graphData: null,
      stats: null,
      searchQuery: '',
      isLoaded: false,
      isLoading: false,
      error: null,
    });
  });

  it('starts with empty state', () => {
    const state = useBrainStore.getState();
    expect(state.nodes).toHaveLength(0);
    expect(state.edges).toHaveLength(0);
    expect(state.isLoaded).toBe(false);
    expect(state.isLoading).toBe(false);
  });

  it('sets loading state', () => {
    useBrainStore.getState().setLoading(true);
    expect(useBrainStore.getState().isLoading).toBe(true);
    useBrainStore.getState().setLoading(false);
    expect(useBrainStore.getState().isLoading).toBe(false);
  });

  it('sets error state', () => {
    useBrainStore.getState().setError('Failed to load');
    expect(useBrainStore.getState().error).toBe('Failed to load');
    useBrainStore.getState().setError(null);
    expect(useBrainStore.getState().error).toBeNull();
  });

  it('sets search query', () => {
    useBrainStore.getState().setSearchQuery('memory test');
    expect(useBrainStore.getState().searchQuery).toBe('memory test');
  });

  it('selects a node', () => {
    useBrainStore.getState().selectNode('node-1');
    expect(useBrainStore.getState().selectedNodeId).toBe('node-1');
    useBrainStore.getState().selectNode(null);
    expect(useBrainStore.getState().selectedNodeId).toBeNull();
  });
});
