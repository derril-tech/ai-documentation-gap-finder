'use client';

import { Gap } from '@/types';
import { getSeverityColor, getStatusColor, getTypeColor, formatDate, truncateText } from '@/lib/utils';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import {
  AlertTriangle,
  FileText,
  Code,
  ExternalLink,
  User,
  Calendar,
  MoreVertical
} from 'lucide-react';

interface GapCardProps {
  gap: Gap;
  onUpdate?: (updates: Partial<Gap>) => void;
  onAssign?: (userId: string) => void;
  compact?: boolean;
}

export function GapCard({ gap, onUpdate, onAssign, compact = false }: GapCardProps) {
  const getGapIcon = (type: string) => {
    switch (type) {
      case 'missing':
        return <AlertTriangle className="h-5 w-5" />;
      case 'broken_link':
        return <ExternalLink className="h-5 w-5" />;
      case 'incorrect_sample':
        return <Code className="h-5 w-5" />;
      default:
        return <FileText className="h-5 w-5" />;
    }
  };

  const getStatusAction = (status: string) => {
    switch (status) {
      case 'open':
        return { label: 'Resolve', action: 'resolved' };
      case 'investigating':
        return { label: 'Mark Resolved', action: 'resolved' };
      case 'resolved':
        return { label: 'Reopen', action: 'open' };
      case 'wont_fix':
        return { label: 'Reopen', action: 'open' };
      default:
        return { label: 'Update', action: 'open' };
    }
  };

  const statusAction = getStatusAction(gap.status);

  if (compact) {
    return (
      <Card className="hover:shadow-md transition-shadow cursor-pointer">
        <CardContent className="p-4">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center space-x-2">
              {getGapIcon(gap.type)}
              <Badge
                variant="secondary"
                className={getTypeColor(gap.type)}
              >
                {gap.type.replace('_', ' ')}
              </Badge>
            </div>
            <div className="flex items-center space-x-1">
              <Badge
                variant="secondary"
                className={getSeverityColor(gap.severity)}
              >
                {gap.severity}
              </Badge>
              <Badge
                variant="secondary"
                className={getStatusColor(gap.status)}
              >
                {gap.status}
              </Badge>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium line-clamp-2">
              {gap.reason || 'No description available'}
            </p>

            {gap.entity && (
              <p className="text-xs text-muted-foreground">
                Entity: {gap.entity.name}
              </p>
            )}

            {gap.doc && (
              <p className="text-xs text-muted-foreground">
                Doc: {gap.doc.title || gap.doc.path}
              </p>
            )}

            <div className="flex items-center justify-between pt-2">
              <span className="text-xs text-muted-foreground">
                Priority: {gap.priority}
              </span>
              <span className="text-xs text-muted-foreground">
                {formatDate(gap.created_at)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            {getGapIcon(gap.type)}
            <div>
              <CardTitle className="text-lg">
                {gap.type.replace('_', ' ').toUpperCase()} Gap
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                ID: {gap.id}
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Badge
              variant="secondary"
              className={getSeverityColor(gap.severity)}
            >
              {gap.severity}
            </Badge>
            <Badge
              variant="secondary"
              className={getStatusColor(gap.status)}
            >
              {gap.status}
            </Badge>
            <Badge
              variant="secondary"
              className={getTypeColor(gap.type)}
            >
              {gap.type.replace('_', ' ')}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Description */}
        <div>
          <h4 className="font-medium mb-2">Description</h4>
          <p className="text-sm text-muted-foreground">
            {gap.reason || 'No description available'}
          </p>
        </div>

        {/* Entity Information */}
        {gap.entity && (
          <div>
            <h4 className="font-medium mb-2">Entity</h4>
            <div className="bg-muted p-3 rounded-md">
              <div className="flex items-center space-x-2 mb-1">
                <Code className="h-4 w-4" />
                <span className="font-medium text-sm">{gap.entity.name}</span>
                <Badge variant="outline" className="text-xs">
                  {gap.entity.kind}
                </Badge>
                <Badge variant="outline" className="text-xs">
                  {gap.entity.lang}
                </Badge>
              </div>
              {gap.entity.path && (
                <p className="text-xs text-muted-foreground font-mono">
                  {gap.entity.path}
                </p>
              )}
              {gap.entity.docstring && (
                <p className="text-xs text-muted-foreground mt-1">
                  {truncateText(gap.entity.docstring, 100)}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Documentation Information */}
        {gap.doc && (
          <div>
            <h4 className="font-medium mb-2">Documentation</h4>
            <div className="bg-muted p-3 rounded-md">
              <div className="flex items-center space-x-2 mb-1">
                <FileText className="h-4 w-4" />
                <span className="font-medium text-sm">
                  {gap.doc.title || 'Untitled'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground font-mono">
                {gap.doc.path}
              </p>
              {gap.doc.last_updated && (
                <p className="text-xs text-muted-foreground mt-1">
                  Last updated: {formatDate(gap.doc.last_updated)}
                </p>
              )}
            </div>
          </div>
        )}

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium">Priority:</span> {gap.priority}
          </div>
          <div>
            <span className="font-medium">Created:</span> {formatDate(gap.created_at)}
          </div>
          <div>
            <span className="font-medium">Updated:</span> {formatDate(gap.updated_at)}
          </div>
          <div>
            <span className="font-medium">Project:</span> {gap.project_id}
          </div>
        </div>

        {/* Actions */}
        {onUpdate && (
          <div className="flex items-center justify-between pt-4 border-t">
            <div className="flex items-center space-x-2">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">
                {formatDate(gap.updated_at)}
              </span>
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onUpdate({ status: statusAction.action })}
              >
                {statusAction.label}
              </Button>

              {onAssign && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onAssign('current-user-id')} // Would be current user
                >
                  <User className="h-4 w-4 mr-1" />
                  Assign
                </Button>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
