import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatusBadge from '../components/StatusBadge';
import PriorityBadge from '../components/PriorityBadge';
import { STATUS, PRIORITY } from '../constants';

describe('StatusBadge', () => {
  it('renders the human-readable label for a known status', () => {
    render(<StatusBadge status={STATUS.IN_PROGRESS} />);
    expect(screen.getByText('In progress')).toBeInTheDocument();
  });

  it('falls back to the raw value for an unknown status', () => {
    render(<StatusBadge status="SOMETHING_UNEXPECTED" />);
    expect(screen.getByText('SOMETHING_UNEXPECTED')).toBeInTheDocument();
  });
});

describe('PriorityBadge', () => {
  it('renders CRITICAL priority, not URGENT (locked Final PSD value)', () => {
    render(<PriorityBadge priority={PRIORITY.CRITICAL} />);
    expect(screen.getByText('Critical')).toBeInTheDocument();
    expect(screen.queryByText('Urgent')).not.toBeInTheDocument();
  });

  it('shows "Unset" when no priority is provided', () => {
    render(<PriorityBadge priority={undefined} />);
    expect(screen.getByText('Unset')).toBeInTheDocument();
  });
});
