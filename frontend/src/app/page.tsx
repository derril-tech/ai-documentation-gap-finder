import { Suspense } from 'react';
import { GapExplorer } from '@/components/gaps/GapExplorer';
import { DashboardStats } from '@/components/dashboard/DashboardStats';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-foreground mb-2">
          AI Documentation Gap Finder
        </h1>
        <p className="text-muted-foreground">
          Automatically detect and fix documentation gaps in your codebase
        </p>
      </div>

      <Suspense fallback={<LoadingSpinner />}>
        <div className="space-y-8">
          <DashboardStats />
          <GapExplorer />
        </div>
      </Suspense>
    </div>
  );
}
