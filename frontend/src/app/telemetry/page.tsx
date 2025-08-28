import { Suspense } from 'react';
import { TelemetryDashboard } from '@/components/telemetry/TelemetryDashboard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function TelemetryPage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <Suspense fallback={<LoadingSpinner />}>
        <TelemetryDashboard projectId="current-project-id" />
      </Suspense>
    </div>
  );
}
