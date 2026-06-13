import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AnansiButton } from '../components/ui/AnansiButton';

describe('AnansiButton', () => {
  it('renders children correctly', () => {
    render(<AnansiButton>Click Me</AnansiButton>);
    expect(screen.getByText('Click Me')).toBeInTheDocument();
  });

  it('applies primary variant by default', () => {
    const { container } = render(<AnansiButton>Primary</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('brand-amber');
  });

  it('applies secondary variant class', () => {
    const { container } = render(<AnansiButton variant="secondary">Secondary</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('glass-interactive');
  });

  it('applies ghost variant class', () => {
    const { container } = render(<AnansiButton variant="ghost">Ghost</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('bg-transparent');
  });

  it('applies danger variant class', () => {
    const { container } = render(<AnansiButton variant="danger">Danger</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('red-600');
  });

  it('applies size classes', () => {
    const { container } = render(<AnansiButton size="lg">Large</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('px-8');
  });

  it('applies fullWidth class when true', () => {
    const { container } = render(<AnansiButton fullWidth>Full Width</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('w-full');
  });

  it('is disabled when disabled prop is true', () => {
    render(<AnansiButton disabled>Disabled</AnansiButton>);
    const button = screen.getByText('Disabled').closest('button');
    expect(button).toBeDisabled();
  });

  it('handles click events', () => {
    const handleClick = vi.fn();
    render(<AnansiButton onClick={handleClick}>Clickable</AnansiButton>);
    fireEvent.click(screen.getByText('Clickable'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('does not fire click when loading', () => {
    const handleClick = vi.fn();
    render(<AnansiButton onClick={handleClick} feedbackState="loading">Loading</AnansiButton>);
    const button = screen.getByText('Loading').closest('button');
    expect(button).toBeDisabled();
  });

  it('shows loading spinner when feedbackState is loading', () => {
    const { container } = render(<AnansiButton feedbackState="loading">Saving</AnansiButton>);
    const spinner = container.querySelector('.animate-spin');
    expect(spinner).toBeInTheDocument();
  });

  it('merges custom className', () => {
    const { container } = render(<AnansiButton className="my-custom-class">Custom</AnansiButton>);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('my-custom-class');
  });
});
