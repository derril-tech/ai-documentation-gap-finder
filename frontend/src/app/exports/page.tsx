import { Suspense } from 'react';
import { ExportWizard } from '@/components/exports/ExportWizard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function ExportsPage() {
  const handleExportComplete = (exportUrl: string) => {
    console.log('Export completed:', exportUrl);
    // In a real implementation, this could show a success message or redirect
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <Suspense fallback={<LoadingSpinner />}>
        <ExportWizard
          projectId="current-project-id" // This would come from context/route params
          onExportComplete={handleExportComplete}
        />
      </Suspense>
    </div>
  );
}
