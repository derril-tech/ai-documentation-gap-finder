'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle
} from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  Download,
  FileText,
  File,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Settings,
  ExternalLink
} from 'lucide-react';
import { apiClient } from '@/lib/api';

interface ExportWizardProps {
  projectId: string;
  onExportComplete?: (exportUrl: string) => void;
}

interface ExportOptions {
  format: 'json' | 'pdf';
  includeDrafts: boolean;
  includeGaps: boolean;
  includeMappings: boolean;
  includeScores: boolean;
  dateRange?: {
    start: string;
    end: string;
  };
}

interface ExportJob {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  format: string;
  createdAt: string;
  completedAt?: string;
  downloadUrl?: string;
  errorMessage?: string;
  fileSize?: number;
}

export function ExportWizard({ projectId, onExportComplete }: ExportWizardProps) {
  const [options, setOptions] = useState<ExportOptions>({
    format: 'json',
    includeDrafts: true,
    includeGaps: true,
    includeMappings: true,
    includeScores: true,
  });

  const [showAdvanced, setShowAdvanced] = useState(false);

  // Fetch recent exports
  const { data: recentExports = [], isLoading: exportsLoading } = useQuery({
    queryKey: ['export-jobs', projectId],
    queryFn: () => apiClient.get(`/projects/${projectId}/exports`),
    staleTime: 1000 * 60, // 1 minute
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: async (exportOptions: ExportOptions) => {
      // In a real implementation, this would call the export API
      // For now, we'll simulate the export
      await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate processing

      // Mock export result
      return {
        id: `export_${Date.now()}`,
        downloadUrl: `/api/exports/download/${Date.now()}.${exportOptions.format}`,
        fileSize: Math.floor(Math.random() * 1000000) + 100000,
      };
    },
    onSuccess: (result) => {
      onExportComplete?.(result.downloadUrl);
    },
  });

  // Fetch project data for context
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => apiClient.getProject(projectId),
    staleTime: 1000 * 60 * 5,
  });

  const handleExport = () => {
    exportMutation.mutate(options);
  };

  const handleDownload = (exportJob: ExportJob) => {
    if (exportJob.downloadUrl) {
      window.open(exportJob.downloadUrl, '_blank');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-600" />;
      case 'running':
        return <Clock className="h-4 w-4 text-blue-600" />;
      case 'pending':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'running':
        return 'bg-blue-100 text-blue-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'pdf':
        return <FileText className="h-4 w-4" />;
      case 'json':
        return <File className="h-4 w-4" />;
      default:
        return <File className="h-4 w-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Export Documentation</h2>
          <p className="text-muted-foreground">
            Generate comprehensive reports and bundles of your documentation analysis
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Export Configuration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Export Configuration</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                <Settings className="h-4 w-4 mr-2" />
                {showAdvanced ? 'Hide' : 'Show'} Advanced
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Format Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Export Format</label>
              <div className="flex gap-2">
                <button
                  onClick={() => setOptions({ ...options, format: 'json' })}
                  className={`flex items-center px-3 py-2 rounded-md border text-sm ${
                    options.format === 'json'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted'
                  }`}
                >
                  <File className="h-4 w-4 mr-2" />
                  JSON
                </button>
                <button
                  onClick={() => setOptions({ ...options, format: 'pdf' })}
                  className={`flex items-center px-3 py-2 rounded-md border text-sm ${
                    options.format === 'pdf'
                      ? 'bg-primary text-primary-foreground border-primary'
                      : 'bg-background hover:bg-muted'
                  }`}
                >
                  <FileText className="h-4 w-4 mr-2" />
                  PDF Report
                </button>
              </div>
            </div>

            {/* Content Selection */}
            <div>
              <label className="block text-sm font-medium mb-2">Include Data</label>
              <div className="space-y-2">
                {[
                  { key: 'includeGaps', label: 'Documentation Gaps' },
                  { key: 'includeDrafts', label: 'Generated Drafts' },
                  { key: 'includeMappings', label: 'Code-Doc Mappings' },
                  { key: 'includeScores', label: 'Quality Scores' },
                ].map(({ key, label }) => (
                  <label key={key} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={options[key as keyof ExportOptions] as boolean}
                      onChange={(e) => setOptions({
                        ...options,
                        [key]: e.target.checked
                      })}
                      className="mr-2"
                    />
                    <span className="text-sm">{label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Advanced Options */}
            {showAdvanced && (
              <div className="border-t pt-4">
                <label className="block text-sm font-medium mb-2">Date Range (Optional)</label>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="date"
                    value={options.dateRange?.start || ''}
                    onChange={(e) => setOptions({
                      ...options,
                      dateRange: {
                        ...options.dateRange,
                        start: e.target.value
                      } as any
                    })}
                    className="px-3 py-2 border border-input rounded-md bg-background text-sm"
                    placeholder="Start date"
                  />
                  <input
                    type="date"
                    value={options.dateRange?.end || ''}
                    onChange={(e) => setOptions({
                      ...options,
                      dateRange: {
                        ...options.dateRange,
                        end: e.target.value
                      } as any
                    })}
                    className="px-3 py-2 border border-input rounded-md bg-background text-sm"
                    placeholder="End date"
                  />
                </div>
              </div>
            )}

            {/* Export Button */}
            <div className="pt-4">
              <Button
                onClick={handleExport}
                disabled={exportMutation.isPending}
                className="w-full"
              >
                {exportMutation.isPending ? (
                  <>
                    <LoadingSpinner size="sm" className="mr-2" />
                    Generating Export...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4 mr-2" />
                    Generate {options.format.toUpperCase()} Export
                  </>
                )}
              </Button>
            </div>

            {/* Export Preview */}
            <div className="bg-muted p-4 rounded-md">
              <h4 className="font-medium mb-2">Export Preview</h4>
              <div className="text-sm space-y-1">
                <div><strong>Format:</strong> {options.format.toUpperCase()}</div>
                <div><strong>Includes:</strong> {
                  [
                    options.includeGaps && 'Gaps',
                    options.includeDrafts && 'Drafts',
                    options.includeMappings && 'Mappings',
                    options.includeScores && 'Scores',
                  ].filter(Boolean).join(', ') || 'None'
                }</div>
                <div><strong>Project:</strong> {project?.name || 'Loading...'}</div>
                {options.dateRange && (
                  <div><strong>Date Range:</strong> {options.dateRange.start} to {options.dateRange.end}</div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recent Exports */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Exports</CardTitle>
          </CardHeader>
          <CardContent>
            {exportsLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : recentExports.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <File className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <p>No exports yet</p>
                <p className="text-sm">Generate your first export to get started</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentExports.slice(0, 5).map((exportJob: ExportJob) => (
                  <div
                    key={exportJob.id}
                    className="flex items-center justify-between p-3 border rounded-md"
                  >
                    <div className="flex items-center space-x-3">
                      {getFormatIcon(exportJob.format)}
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium text-sm">
                            {exportJob.format.toUpperCase()} Export
                          </span>
                          <Badge
                            variant="secondary"
                            className={getStatusColor(exportJob.status)}
                          >
                            {getStatusIcon(exportJob.status)}
                            <span className="ml-1 capitalize">{exportJob.status}</span>
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {new Date(exportJob.createdAt).toLocaleString()}
                          {exportJob.fileSize && ` • ${formatFileSize(exportJob.fileSize)}`}
                        </div>
                      </div>
                    </div>

                    {exportJob.status === 'completed' && exportJob.downloadUrl && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(exportJob)}
                      >
                        <Download className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Export Result */}
      {exportMutation.isSuccess && (
        <Card className="border-green-200 bg-green-50">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <h4 className="font-medium text-green-800">Export Completed Successfully!</h4>
                <p className="text-sm text-green-700">
                  Your {options.format.toUpperCase()} export is ready for download.
                </p>
                <div className="flex items-center space-x-2 mt-2">
                  <Button
                    size="sm"
                    onClick={() => window.open(exportMutation.data.downloadUrl, '_blank')}
                  >
                    <Download className="h-4 w-4 mr-2" />
                    Download Export
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportMutation.reset()}
                  >
                    Generate Another
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {exportMutation.isError && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <XCircle className="h-5 w-5 text-red-600" />
              <div>
                <h4 className="font-medium text-red-800">Export Failed</h4>
                <p className="text-sm text-red-700">
                  {apiClient.getErrorMessage(exportMutation.error)}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => exportMutation.reset()}
                  className="mt-2"
                >
                  Try Again
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export Tips */}
      <Card>
        <CardHeader>
          <CardTitle>Export Tips</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div className="flex items-start space-x-2">
              <FileText className="h-4 w-4 mt-0.5 text-blue-600" />
              <div>
                <strong>JSON Export:</strong> Comprehensive data for programmatic analysis and integration with other tools.
              </div>
            </div>
            <div className="flex items-start space-x-2">
              <File className="h-4 w-4 mt-0.5 text-red-600" />
              <div>
                <strong>PDF Report:</strong> Professional documentation with charts, tables, and executive summaries.
              </div>
            </div>
            <div className="flex items-start space-x-2">
              <ExternalLink className="h-4 w-4 mt-0.5 text-green-600" />
              <div>
                <strong>Best Practices:</strong> Include all data types for comprehensive analysis. Use date ranges to focus on specific time periods.
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
