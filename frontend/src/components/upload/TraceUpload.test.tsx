'use client';

import { fireEvent, render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { TraceUpload } from './TraceUpload';

const mutateAsync = vi.fn().mockResolvedValue({ trace: { id: 'trace-123' } });
vi.mock('@/hooks/useTraces', () => ({ useUploadTrace: () => ({ mutateAsync, isPending: false }) }));

describe('TraceUpload shared flow', () => {
  it('uses the trace mutation and returns a trace id only', async () => {
    const onUploadSuccess = vi.fn();
    const { getByTestId } = render(<TraceUpload onUploadSuccess={onUploadSuccess} />);
    const file = new File(['gpx'], 'course.gpx', { type: 'application/gpx+xml' });
    fireEvent.change(getByTestId('trace-upload-input'), { target: { files: [file] } });
    await waitFor(() => expect(mutateAsync).toHaveBeenCalledWith({ file, name: 'course.gpx' }));
    await waitFor(() => expect(onUploadSuccess).toHaveBeenCalledWith('trace-123'));
    expect(onUploadSuccess).not.toHaveBeenCalledWith(expect.anything(), expect.anything());
  });
});
