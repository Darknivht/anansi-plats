import { render, screen } from '@testing-library/react';
import GlassCard from '../components/ui/GlassCard';
import { describe, it, expect } from 'vitest';

describe('GlassCard', () => {
  it('renders children correctly', () => {
    render(<GlassCard>Hello World</GlassCard>);
    expect(screen.getByText('Hello World')).toBeInTheDocument();
  });

  it('applies base variant class by default', () => {
    const { container } = render(<GlassCard>Card Content</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glass-card');
  });

  it('applies elevated variant class', () => {
    const { container } = render(<GlassCard variant="elevated">Elevated</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glass-elevated');
  });

  it('applies interactive variant class', () => {
    const { container } = render(<GlassCard variant="interactive">Interactive</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glass-interactive');
  });

  it('applies glow effect class', () => {
    const { container } = render(<GlassCard glow="amber">Glowing Card</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('glow-amber');
  });

  it('applies padding class', () => {
    const { container } = render(<GlassCard padding="lg">Large Padding</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('p-8');
  });

  it('merges custom className', () => {
    const { container } = render(<GlassCard className="custom-class">Custom</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.className).toContain('custom-class');
  });

  it('renders as button when onClick is provided', () => {
    const { container } = render(<GlassCard onClick={() => {}}>Clickable</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.tagName).toBe('BUTTON');
  });

  it('renders as div when no onClick', () => {
    const { container } = render(<GlassCard>Static</GlassCard>);
    const card = container.firstChild as HTMLElement;
    expect(card.tagName).toBe('DIV');
  });
});
