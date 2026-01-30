'use client';

import { fireEvent, render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { ActivityUpload } from './ActivityUpload';

const mutateAsync = vi.fn().mockResolvedValue({ id: 'activity-123', type: 'real' });

vi.mock('@/hooks/useActivity', () => ({
  useUploadActivity: () => ({
    mutateAsync,
    isPending: false,
  }),
}));

describe('ActivityUpload', () => {
  it('uploads a file and calls onUploadSuccess', async () => {
    const onUploadSuccess = vi.fn();
    const { container } = render(<ActivityUpload onUploadSuccess={onUploadSuccess} />);

    const input = container.querySelector('input[type="file"]') as HTMLInputElement | null;
    expect(input).not.toBeNull();
    if (!input) return;

    const file = new File(['data'], 'sample.gpx', { type: 'application/gpx+xml' });
    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ file, name: 'sample.gpx' }));
    await waitFor(() => expect(onUploadSuccess).toHaveBeenCalledWith('activity-123', 'real'));
  });
});
