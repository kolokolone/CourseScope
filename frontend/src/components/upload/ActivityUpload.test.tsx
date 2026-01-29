import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

import { ActivityUpload } from './ActivityUpload';

const mockMutateAsync = vi.fn();

vi.mock('@/hooks/useActivity', () => ({
  useUploadActivity: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

describe('ActivityUpload', () => {
  it('uploads a valid file and calls onUploadSuccess', async () => {
    mockMutateAsync.mockResolvedValueOnce({ id: 'activity-1', type: 'real' });

    const onUploadSuccess = vi.fn();
    const user = userEvent.setup();

    const { container } = render(<ActivityUpload onUploadSuccess={onUploadSuccess} />);

    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['gpx'], 'run.gpx', { type: 'application/gpx+xml' });

    await user.upload(input, file);

    expect(screen.getByText('run.gpx')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Upload Activity' }));

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledWith({ file, name: 'run.gpx' });
    });

    expect(onUploadSuccess).toHaveBeenCalledWith('activity-1', 'real');
  });
});
