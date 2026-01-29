import { ReactNode } from 'react';
import Link from 'next/link';

interface ActivityLayoutProps {
  children: ReactNode;
}

export default async function ActivityLayout({ children }: ActivityLayoutProps) {
  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="mb-6">
        <nav className="flex items-center space-x-4">
          <Link
            href="/"
            className="text-gray-600 hover:text-gray-900 transition-colors"
          >
            ← Back to Activities
          </Link>
        </nav>
      </div>
      {children}
    </div>
  );
}
