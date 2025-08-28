'use client';

import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Gap,
  GapFilters,
  Project,
  User,
  GapType,
  GapSeverity,
  GapStatus
} from '@/types';
import { apiClient } from '@/lib/api';
import { GapTable } from './GapTable';
import { GapFiltersPanel } from './GapFiltersPanel';
import { GapCard } from './GapCard';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Grid, List, Filter } from 'lucide-react';

export function GapExplorer() {
  const [filters, setFilters] = useState<GapFilters>({
    status: ['open'],
    page: 1,
    limit: 20,
    sort_by: 'priority',
    sort_order: 'desc',
  });

  const [viewMode, setViewMode] = useState<'table' | 'cards'>('table');
  const [selectedGap, setSelectedGap] = useState<Gap | null>(null);
  const [showFilters, setShowFilters] = useState(false);

  const queryClient = useQueryClient();

  // Fetch gaps
  const {
    data: gapsResponse,
    isLoading: gapsLoading,
    error: gapsError,
  } = useQuery({
    queryKey: ['gaps', filters],
    queryFn: () => apiClient.getGaps(filters),
    staleTime: 1000 * 60, // 1 minute
  });

  // Fetch projects for filters
  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: () => apiClient.getProjects(),
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  // Update gap mutation
  const updateGapMutation = useMutation({
    mutationFn: ({ gapId, updates }: { gapId: string; updates: Partial<Gap> }) =>
      apiClient.updateGap(gapId, updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['gaps'] });
    },
  });

  const gaps = gapsResponse?.data || [];
  const pagination = gapsResponse?.pagination;

  const handleFiltersChange = (newFilters: GapFilters) => {
    setFilters({ ...newFilters, page: 1 }); // Reset to first page
  };

  const handleGapSelect = (gap: Gap) => {
    setSelectedGap(gap);
  };

  const handleGapUpdate = (gapId: string, updates: Partial<Gap>) => {
    updateGapMutation.mutate({ gapId, updates });
  };

  const handlePageChange = (page: number) => {
    setFilters({ ...filters, page });
  };

  if (gapsError) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>Failed to load gaps: {apiClient.getErrorMessage(gapsError)}</p>
            <Button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['gaps'] })}
              className="mt-4"
            >
              Retry
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Gap Explorer</h2>
          <p className="text-muted-foreground">
            Discover and manage documentation gaps in your projects
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center space-x-2"
          >
            <Filter className="h-4 w-4" />
            <span>Filters</span>
          </Button>

          <div className="flex items-center border rounded-md">
            <Button
              variant={viewMode === 'table' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('table')}
              className="rounded-r-none"
            >
              <List className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'cards' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('cards')}
              className="rounded-l-none border-l"
            >
              <Grid className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent>
            <GapFiltersPanel
              filters={filters}
              projects={projects}
              onChange={handleFiltersChange}
            />
          </CardContent>
        </Card>
      )}

      {/* Results Summary */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {pagination ? (
            <>
              Showing {((pagination.page - 1) * pagination.limit) + 1} to{' '}
              {Math.min(pagination.page * pagination.limit, pagination.total)} of{' '}
              {pagination.total} gaps
            </>
          ) : (
            `${gaps.length} gaps loaded`
          )}
        </span>

        {pagination && pagination.total_pages > 1 && (
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page <= 1}
              onClick={() => handlePageChange(pagination.page - 1)}
            >
              Previous
            </Button>

            <span className="px-3 py-1 bg-muted rounded">
              Page {pagination.page} of {pagination.total_pages}
            </span>

            <Button
              variant="outline"
              size="sm"
              disabled={pagination.page >= pagination.total_pages}
              onClick={() => handlePageChange(pagination.page + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>

      {/* Content */}
      {gapsLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : gaps.length === 0 ? (
        <Card>
          <CardContent className="p-12">
            <div className="text-center">
              <div className="text-6xl mb-4">🔍</div>
              <h3 className="text-lg font-semibold mb-2">No gaps found</h3>
              <p className="text-muted-foreground mb-4">
                {filters.project_id
                  ? "Try adjusting your filters or scan this project for gaps."
                  : "Select a project to view its documentation gaps."
                }
              </p>
              {filters.project_id && (
                <Button
                  onClick={() => apiClient.startProjectScan(filters.project_id!, 'full')}
                >
                  Start Full Scan
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : viewMode === 'table' ? (
        <GapTable
          gaps={gaps}
          loading={gapsLoading}
          onGapSelect={handleGapSelect}
          onGapUpdate={handleGapUpdate}
          filters={filters}
          onFiltersChange={handleFiltersChange}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {gaps.map((gap) => (
            <GapCard
              key={gap.id}
              gap={gap}
              onUpdate={(updates) => handleGapUpdate(gap.id, updates)}
              compact
            />
          ))}
        </div>
      )}

      {/* Selected Gap Details */}
      {selectedGap && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Gap Details</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedGap(null)}
              >
                ×
              </Button>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <GapCard
              gap={selectedGap}
              onUpdate={(updates) => handleGapUpdate(selectedGap.id, updates)}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
