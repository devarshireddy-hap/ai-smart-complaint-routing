import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import CreateComplaint from '../pages/CreateComplaint';
import { complaintsApi } from '../services/api';

vi.mock('../services/api', () => ({
  complaintsApi: { create: vi.fn() },
  ApiError: class ApiError extends Error {},
}));

describe('CreateComplaint', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('blocks submission when title and description are empty', async () => {
    render(
      <MemoryRouter>
        <CreateComplaint />
      </MemoryRouter>
    );
    await userEvent.click(screen.getByRole('button', { name: /submit complaint/i }));

    expect(await screen.findByText('Title is required.')).toBeInTheDocument();
    expect(screen.getByText('Description is required.')).toBeInTheDocument();
    expect(complaintsApi.create).not.toHaveBeenCalled();
  });

  it('submits trimmed values when the form is valid', async () => {
    complaintsApi.create.mockResolvedValue({ complaint_id: 'abc-123' });

    render(
      <MemoryRouter>
        <CreateComplaint />
      </MemoryRouter>
    );

    await userEvent.type(screen.getByLabelText('Title'), '  Broken light  ');
    await userEvent.type(screen.getByLabelText('Description'), '  It has been off for days.  ');
    await userEvent.click(screen.getByRole('button', { name: /submit complaint/i }));

    await waitFor(() =>
      expect(complaintsApi.create).toHaveBeenCalledWith({
        title: 'Broken light',
        description: 'It has been off for days.',
      })
    );
  });
});
