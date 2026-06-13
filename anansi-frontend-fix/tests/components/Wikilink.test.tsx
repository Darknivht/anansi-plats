import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Wikilink } from '../components/ui/Wikilink';

describe('Wikilink', () => {
  it('renders the target text', () => {
    render(<Wikilink target="Second Brain" />);
    expect(screen.getByText('Second Brain')).toBeInTheDocument();
  });

  it('renders custom label when provided', () => {
    render(<Wikilink target="Second Brain" label="Brain" />);
    expect(screen.getByText('Brain')).toBeInTheDocument();
    expect(screen.queryByText('Second Brain')).not.toBeInTheDocument();
  });

  it('calls onClick with target when clicked', () => {
    const handleClick = vi.fn();
    render(<Wikilink target="Project Alpha" onClick={handleClick} />);
    fireEvent.click(screen.getByText('Project Alpha'));
    expect(handleClick).toHaveBeenCalledWith('Project Alpha');
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('applies unresolved styling when unresolved is true', () => {
    const { container } = render(<Wikilink target="New Node" unresolved />);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('amber-400/60');
    expect(button.className).not.toContain('hover:shadow-glow-amber');
  });

  it('applies resolved styling by default', () => {
    const { container } = render(<Wikilink target="Existing Node" />);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('hover:shadow-glow-amber');
  });

  it('merges custom className', () => {
    const { container } = render(<Wikilink target="Test" className="extra-class" />);
    const button = container.firstChild as HTMLElement;
    expect(button.className).toContain('extra-class');
  });

  it('has correct aria-label', () => {
    render(<Wikilink target="My Memory" />);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('aria-label', 'Open memory: My Memory');
  });

  it('has correct title attribute', () => {
    render(<Wikilink target="My Memory" />);
    const button = screen.getByRole('button');
    expect(button).toHaveAttribute('title', 'Open [[My Memory]]');
  });
});
