'use client';

import { useState } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
} from '@tanstack/react-table';
import { ChevronUp, ChevronDown, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { Gap, GapFilters, Project } from '@/types';
import { getSeverityColor, getStatusColor, getTypeColor, formatDate } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';

interface GapTableProps {
  gaps: Gap[];
  loading?: boolean;
  onGapSelect?: (gap: Gap) => void;
  onGapUpdate?: (gapId: string, updates: Partial<Gap>) => void;
  filters?: GapFilters;
  onFiltersChange?: (filters: GapFilters) => void;
  projects?: Project[];
}

export function GapTable({
  gaps,
  loading,
  onGapSelect,
  onGapUpdate,
  filters,
  onFiltersChange,
  projects = [],
}: GapTableProps) {
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'priority', desc: true },
  ]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);

  const columns: ColumnDef<Gap>[] = [
    {
      accessorKey: 'type',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-semibold"
        >
          Type
          {column.getIsSorted() === 'asc' ? (
            <ChevronUp className="ml-2 h-4 w-4" />
          ) : column.getIsSorted() === 'desc' ? (
            <ChevronDown className="ml-2 h-4 w-4" />
          ) : (
            <ArrowUpDown className="ml-2 h-4 w-4" />
          )}
        </Button>
      ),
      cell: ({ row }) => (
        <Badge
          variant="secondary"
          className={getTypeColor(row.getValue('type'))}
        >
          {row.getValue('type')}
        </Badge>
      ),
    },
    {
      accessorKey: 'severity',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-semibold"
        >
          Severity
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <Badge
          variant="secondary"
          className={getSeverityColor(row.getValue('severity'))}
        >
          {row.getValue('severity')}
        </Badge>
      ),
    },
    {
      accessorKey: 'priority',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-semibold"
        >
          Priority
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="text-center">
          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
            {row.getValue('priority')}
          </span>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => (
        <Badge
          variant="secondary"
          className={getStatusColor(row.getValue('status'))}
        >
          {row.getValue('status')}
        </Badge>
      ),
    },
    {
      accessorKey: 'entity.name',
      header: 'Entity',
      cell: ({ row }) => {
        const entity = row.original.entity;
        return (
          <div className="max-w-xs">
            <div className="font-medium text-sm truncate">
              {entity?.name || 'N/A'}
            </div>
            {entity?.path && (
              <div className="text-xs text-muted-foreground truncate">
                {entity.path}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'doc.path',
      header: 'Documentation',
      cell: ({ row }) => {
        const doc = row.original.doc;
        return (
          <div className="max-w-xs">
            <div className="text-sm truncate">
              {doc?.path || 'N/A'}
            </div>
            {doc?.title && (
              <div className="text-xs text-muted-foreground truncate">
                {doc.title}
              </div>
            )}
          </div>
        );
      },
    },
    {
      accessorKey: 'reason',
      header: 'Reason',
      cell: ({ row }) => (
        <div className="max-w-sm">
          <p className="text-sm text-muted-foreground line-clamp-2">
            {row.getValue('reason')}
          </p>
        </div>
      ),
    },
    {
      accessorKey: 'created_at',
      header: ({ column }) => (
        <Button
          variant="ghost"
          onClick={() => column.toggleSorting(column.getIsSorted() === 'asc')}
          className="h-auto p-0 font-semibold"
        >
          Created
          <ArrowUpDown className="ml-2 h-4 w-4" />
        </Button>
      ),
      cell: ({ row }) => (
        <div className="text-sm text-muted-foreground">
          {formatDate(row.getValue('created_at'))}
        </div>
      ),
    },
    {
      id: 'actions',
      header: 'Actions',
      cell: ({ row }) => (
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onGapSelect?.(row.original)}
          >
            View
          </Button>
          {onGapUpdate && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onGapUpdate(row.original.id, {
                status: row.original.status === 'open' ? 'resolved' : 'open'
              })}
            >
              {row.original.status === 'open' ? 'Resolve' : 'Reopen'}
            </Button>
          )}
        </div>
      ),
    },
  ];

  const table = useReactTable({
    data: gaps,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    state: {
      sorting,
      columnFilters,
      pagination: {
        pageIndex: (filters?.page || 1) - 1,
        pageSize: filters?.limit || 20,
      },
    },
  });

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-md border">
        <table className="w-full">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b bg-muted/50">
                {headerGroup.headers.map((header) => (
                  <th
                    key={header.id}
                    className="h-12 px-4 text-left align-middle font-medium text-muted-foreground"
                  >
                    {header.isPlaceholder
                      ? null
                      : header.column.getCanSort()
                      ? header.column.columnDef.header
                      : header.column.columnDef.header}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b hover:bg-muted/50 cursor-pointer"
                  onClick={() => onGapSelect?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="p-4 align-middle">
                      {cell.column.columnDef.cell
                        ? cell.column.columnDef.cell(cell.getContext())
                        : cell.getValue()}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="h-24 text-center">
                  No gaps found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-2">
        <div className="flex-1 text-sm text-muted-foreground">
          {table.getFilteredSelectedRowModel().rows.length} of{' '}
          {table.getFilteredRowModel().rows.length} row(s) selected.
        </div>
        <div className="flex items-center space-x-6 lg:space-x-8">
          <div className="flex items-center space-x-2">
            <p className="text-sm font-medium">Rows per page</p>
            <select
              value={table.getState().pagination.pageSize}
              onChange={(e) => {
                table.setPageSize(Number(e.target.value));
                onFiltersChange?.({
                  ...filters,
                  limit: Number(e.target.value),
                  page: 1,
                });
              }}
              className="h-8 w-[70px] rounded border border-input bg-transparent px-3 py-1 text-sm ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              {[10, 20, 30, 40, 50].map((pageSize) => (
                <option key={pageSize} value={pageSize}>
                  {pageSize}
                </option>
              ))}
            </select>
          </div>
          <div className="flex w-[100px] items-center justify-center text-sm font-medium">
            Page {table.getState().pagination.pageIndex + 1} of{' '}
            {table.getPageCount()}
          </div>
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => {
                table.previousPage();
                onFiltersChange?.({
                  ...filters,
                  page: (filters?.page || 1) - 1,
                });
              }}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              className="h-8 w-8 p-0"
              onClick={() => {
                table.nextPage();
                onFiltersChange?.({
                  ...filters,
                  page: (filters?.page || 1) + 1,
                });
              }}
              disabled={!table.getCanNextPage()}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
