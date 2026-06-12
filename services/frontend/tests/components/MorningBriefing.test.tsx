import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MorningBriefing } from '@/components/features/MorningBriefing';

describe('MorningBriefing', () => {
  it('renders the title', () => {
    render(<MorningBriefing />);
    expect(screen.getByText('Morning Briefing')).toBeInTheDocument();
  });

  it('renders the current date', () => {
    const testDate = new Date('2026-06-12');
    render(<MorningBriefing date={testDate} />);
    const dateStr = testDate.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
    expect(screen.getByText(dateStr)).toBeInTheDocument();
  });

  it('renders agenda items', () => {
    render(<MorningBriefing />);
    expect(screen.getByText('Design Review')).toBeInTheDocument();
    expect(screen.getByText('Client Call — TechCo')).toBeInTheDocument();
    expect(screen.getByText('Gym')).toBeInTheDocument();
  });

  it('renders AI suggestion text', () => {
    render(<MorningBriefing />);
    expect(screen.getByText(/I noticed you haven/)).toBeInTheDocument();
  });

  it('calls onRefresh when refresh button is clicked', () => {
    const handleRefresh = vi.fn();
    render(<MorningBriefing onRefresh={handleRefresh} />);
    const refreshBtn = screen.getByLabelText('Refresh briefing');
    fireEvent.click(refreshBtn);
    expect(handleRefresh).toHaveBeenCalledOnce();
  });

  it('calls onSettings when settings button is clicked', () => {
    const handleSettings = vi.fn();
    render(<MorningBriefing onSettings={handleSettings} />);
    const settingsBtn = screen.getByLabelText('Briefing settings');
    fireEvent.click(settingsBtn);
    expect(handleSettings).toHaveBeenCalledOnce();
  });

  it('applies custom className', () => {
    const { container } = render(<MorningBriefing className="test-class" />);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('test-class');
  });
});
