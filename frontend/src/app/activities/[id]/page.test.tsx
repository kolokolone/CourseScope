import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import ActivityPage from './page';

vi.mock('next/navigation', () => ({ useParams: () => ({ id: 'activity-1' }) }));
vi.mock('@/components/activity-beta/ActivityBetaPage', () => ({
  ActivityBetaPage: ({ activityId }: { activityId: string }) => <div>Nouvelle analyse {activityId}</div>,
}));

describe('ActivityPage', () => {
  it('uses the beta analysis as the canonical activity page', () => {
    render(<ActivityPage />);
    expect(screen.getByText('Nouvelle analyse activity-1')).toBeInTheDocument();
  });
});
