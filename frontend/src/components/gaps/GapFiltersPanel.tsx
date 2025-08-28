'use client';

import { GapFilters, GapType, GapSeverity, GapStatus, Project } from '@/types';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface GapFiltersPanelProps {
  filters: GapFilters;
  projects: Project[];
  onChange: (filters: GapFilters) => void;
}

export function GapFiltersPanel({ filters, projects, onChange }: GapFiltersPanelProps) {
  const gapTypes: GapType[] = [
    'missing',
    'partial',
    'stale',
    'broken_link',
    'incorrect_sample',
    'orphan_doc',
    'outdated_screenshot'
  ];

  const gapSeverities: GapSeverity[] = ['low', 'medium', 'high', 'critical'];
  const gapStatuses: GapStatus[] = ['open', 'investigating', 'resolved', 'wont_fix'];

  const updateFilter = <K extends keyof GapFilters>(
    key: K,
    value: GapFilters[K]
  ) => {
    onChange({ ...filters, [key]: value });
  };

  const toggleArrayFilter = <T,>(
    current: T[] | undefined,
    value: T
  ): T[] => {
    if (!current) return [value];
    return current.includes(value)
      ? current.filter(v => v !== value)
      : [...current, value];
  };

  const clearFilters = () => {
    onChange({
      page: 1,
      limit: 20,
      sort_by: 'priority',
      sort_order: 'desc',
    });
  };

  const hasActiveFilters = !!(
    filters.type?.length ||
    filters.severity?.length ||
    filters.status?.length ||
    filters.project_id ||
    filters.search
  );

  return (
    <div className="space-y-6">
      {/* Search */}
      <div>
        <label className="block text-sm font-medium mb-2">Search</label>
        <input
          type="text"
          placeholder="Search gaps..."
          value={filters.search || ''}
          onChange={(e) => updateFilter('search', e.target.value)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
        />
      </div>

      {/* Project Filter */}
      <div>
        <label className="block text-sm font-medium mb-2">Project</label>
        <select
          value={filters.project_id || ''}
          onChange={(e) => updateFilter('project_id', e.target.value || undefined)}
          className="w-full px-3 py-2 border border-input rounded-md bg-background"
        >
          <option value="">All Projects</option>
          {projects.map((project) => (
            <option key={project.id} value={project.id}>
              {project.name}
            </option>
          ))}
        </select>
      </div>

      {/* Type Filters */}
      <div>
        <label className="block text-sm font-medium mb-2">Gap Types</label>
        <div className="flex flex-wrap gap-2">
          {gapTypes.map((type) => (
            <button
              key={type}
              onClick={() => updateFilter('type', toggleArrayFilter(filters.type, type))}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filters.type?.includes(type)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
            >
              {type.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Severity Filters */}
      <div>
        <label className="block text-sm font-medium mb-2">Severity</label>
        <div className="flex flex-wrap gap-2">
          {gapSeverities.map((severity) => (
            <button
              key={severity}
              onClick={() => updateFilter('severity', toggleArrayFilter(filters.severity, severity))}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filters.severity?.includes(severity)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
            >
              {severity}
            </button>
          ))}
        </div>
      </div>

      {/* Status Filters */}
      <div>
        <label className="block text-sm font-medium mb-2">Status</label>
        <div className="flex flex-wrap gap-2">
          {gapStatuses.map((status) => (
            <button
              key={status}
              onClick={() => updateFilter('status', toggleArrayFilter(filters.status, status))}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                filters.status?.includes(status)
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
              }`}
            >
              {status.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Sort Options */}
      <div>
        <label className="block text-sm font-medium mb-2">Sort By</label>
        <div className="flex gap-4">
          <select
            value={filters.sort_by || 'priority'}
            onChange={(e) => updateFilter('sort_by', e.target.value as any)}
            className="px-3 py-2 border border-input rounded-md bg-background"
          >
            <option value="priority">Priority</option>
            <option value="created_at">Created Date</option>
            <option value="severity">Severity</option>
            <option value="type">Type</option>
          </select>
          <select
            value={filters.sort_order || 'desc'}
            onChange={(e) => updateFilter('sort_order', e.target.value as any)}
            className="px-3 py-2 border border-input rounded-md bg-background"
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </div>
      </div>

      {/* Active Filters Summary */}
      {hasActiveFilters && (
        <div>
          <label className="block text-sm font-medium mb-2">Active Filters</label>
          <div className="flex flex-wrap gap-2">
            {filters.type?.map((type) => (
              <Badge key={type} variant="secondary">
                Type: {type.replace('_', ' ')}
                <button
                  onClick={() => updateFilter('type', filters.type?.filter(t => t !== type))}
                  className="ml-2 text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </Badge>
            ))}
            {filters.severity?.map((severity) => (
              <Badge key={severity} variant="secondary">
                Severity: {severity}
                <button
                  onClick={() => updateFilter('severity', filters.severity?.filter(s => s !== severity))}
                  className="ml-2 text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </Badge>
            ))}
            {filters.status?.map((status) => (
              <Badge key={status} variant="secondary">
                Status: {status.replace('_', ' ')}
                <button
                  onClick={() => updateFilter('status', filters.status?.filter(s => s !== status))}
                  className="ml-2 text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </Badge>
            ))}
            {filters.project_id && (
              <Badge variant="secondary">
                Project: {projects.find(p => p.id === filters.project_id)?.name || filters.project_id}
                <button
                  onClick={() => updateFilter('project_id', undefined)}
                  className="ml-2 text-muted-foreground hover:text-foreground"
                >
                  ×
                </button>
              </Badge>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Button
          onClick={clearFilters}
          variant="outline"
          disabled={!hasActiveFilters}
          className="flex-1"
        >
          Clear All Filters
        </Button>
      </div>
    </div>
  );
}
