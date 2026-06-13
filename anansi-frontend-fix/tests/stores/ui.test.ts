import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '../stores/ui';

describe('UI Store', () => {
  beforeEach(() => {
    // Reset store to defaults
    useUIStore.setState({
      sidebarOpen: true,
      sidebarExpanded: true,
      activeModal: null,
      modalData: null,
      theme: 'dark',
      toasts: [],
      commandPaletteOpen: false,
    });
  });

  describe('Sidebar', () => {
    it('toggles sidebar open state', () => {
      expect(useUIStore.getState().sidebarOpen).toBe(true);
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarOpen).toBe(false);
      useUIStore.getState().toggleSidebar();
      expect(useUIStore.getState().sidebarOpen).toBe(true);
    });

    it('sets sidebar expanded state', () => {
      useUIStore.getState().setSidebarExpanded(false);
      expect(useUIStore.getState().sidebarExpanded).toBe(false);
      useUIStore.getState().setSidebarExpanded(true);
      expect(useUIStore.getState().sidebarExpanded).toBe(true);
    });
  });

  describe('Modals', () => {
    it('opens a modal with data', () => {
      useUIStore.getState().openModal('test-modal', { key: 'value' });
      expect(useUIStore.getState().activeModal).toBe('test-modal');
      expect(useUIStore.getState().modalData).toEqual({ key: 'value' });
    });

    it('closes the active modal', () => {
      useUIStore.getState().openModal('test-modal', 'data');
      expect(useUIStore.getState().activeModal).toBe('test-modal');
      useUIStore.getState().closeModal();
      expect(useUIStore.getState().activeModal).toBeNull();
      expect(useUIStore.getState().modalData).toBeNull();
    });
  });

  describe('Theme', () => {
    it('sets theme', () => {
      useUIStore.getState().setTheme('light');
      expect(useUIStore.getState().theme).toBe('light');
    });

    it('toggles theme between dark and light', () => {
      expect(useUIStore.getState().theme).toBe('dark');
      useUIStore.getState().toggleTheme();
      expect(useUIStore.getState().theme).toBe('light');
      useUIStore.getState().toggleTheme();
      expect(useUIStore.getState().theme).toBe('dark');
    });
  });

  describe('Toasts', () => {
    it('adds a toast and returns its ID', () => {
      const id = useUIStore.getState().addToast('success', 'Saved!', 'Data saved successfully');
      expect(id).toBeDefined();
      const toasts = useUIStore.getState().toasts;
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe('success');
      expect(toasts[0].title).toBe('Saved!');
      expect(toasts[0].message).toBe('Data saved successfully');
    });

    it('removes a toast by ID', () => {
      const id = useUIStore.getState().addToast('error', 'Error!');
      expect(useUIStore.getState().toasts).toHaveLength(1);
      useUIStore.getState().removeToast(id);
      expect(useUIStore.getState().toasts).toHaveLength(0);
    });

    it('auto-removes toast after duration', async () => {
      vi.useFakeTimers();
      useUIStore.getState().addToast('info', 'Auto-remove', undefined, 100);
      expect(useUIStore.getState().toasts).toHaveLength(1);
      vi.advanceTimersByTime(100);
      expect(useUIStore.getState().toasts).toHaveLength(0);
      vi.useRealTimers();
    });
  });

  describe('Command Palette', () => {
    it('toggles command palette', () => {
      expect(useUIStore.getState().commandPaletteOpen).toBe(false);
      useUIStore.getState().toggleCommandPalette();
      expect(useUIStore.getState().commandPaletteOpen).toBe(true);
      useUIStore.getState().toggleCommandPalette();
      expect(useUIStore.getState().commandPaletteOpen).toBe(false);
    });

    it('sets command palette open state', () => {
      useUIStore.getState().setCommandPaletteOpen(true);
      expect(useUIStore.getState().commandPaletteOpen).toBe(true);
      useUIStore.getState().setCommandPaletteOpen(false);
      expect(useUIStore.getState().commandPaletteOpen).toBe(false);
    });
  });
});
