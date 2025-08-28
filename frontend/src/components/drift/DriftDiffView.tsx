'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Minus,
  Edit,
  AlertTriangle,
  CheckCircle,
  Info,
  GitBranch,
  FileText,
  Code
} from 'lucide-react';

interface DriftDiff {
  id: string;
  type: 'endpoint' | 'schema' | 'parameter' | 'response' | 'type';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'new' | 'modified' | 'removed' | 'deprecated';
  path: string;
  specValue: any;
  implValue: any;
  description: string;
  suggestions: string[];
  lineNumber?: number;
}

interface DriftDiffViewProps {
  drifts: DriftDiff[];
  specTitle?: string;
  implTitle?: string;
  onAcceptDrift?: (driftId: string) => void;
  onIgnoreDrift?: (driftId: string) => void;
  onGenerateFix?: (driftId: string) => void;
}

export function DriftDiffView({
  drifts,
  specTitle = "API Specification",
  implTitle = "Current Implementation",
  onAcceptDrift,
  onIgnoreDrift,
  onGenerateFix,
}: DriftDiffViewProps) {
  const [expandedDrifts, setExpandedDrifts] = useState<Set<string>>(new Set());
  const [viewMode, setViewMode] = useState<'unified' | 'split'>('split');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  const toggleDrift = (driftId: string) => {
    const newExpanded = new Set(expandedDrifts);
    if (newExpanded.has(driftId)) {
      newExpanded.delete(driftId);
    } else {
      newExpanded.add(driftId);
    }
    setExpandedDrifts(newExpanded);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'new':
        return <Plus className="h-4 w-4 text-green-600" />;
      case 'modified':
        return <Edit className="h-4 w-4 text-blue-600" />;
      case 'removed':
        return <Minus className="h-4 w-4 text-red-600" />;
      case 'deprecated':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      default:
        return <Info className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'new':
        return 'bg-green-100 text-green-800';
      case 'modified':
        return 'bg-blue-100 text-blue-800';
      case 'removed':
        return 'bg-red-100 text-red-800';
      case 'deprecated':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'text-red-600 bg-red-100';
      case 'high':
        return 'text-orange-600 bg-orange-100';
      case 'medium':
        return 'text-yellow-600 bg-yellow-100';
      case 'low':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'endpoint':
        return <GitBranch className="h-4 w-4" />;
      case 'schema':
        return <FileText className="h-4 w-4" />;
      case 'parameter':
        return <Code className="h-4 w-4" />;
      case 'response':
        return <CheckCircle className="h-4 w-4" />;
      case 'type':
        return <Info className="h-4 w-4" />;
      default:
        return <Info className="h-4 w-4" />;
    }
  };

  const renderValue = (value: any, title: string) => {
    if (value === null || value === undefined) {
      return (
        <div className="text-sm text-muted-foreground italic">
          {title}: Not defined
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div>
          <div className="text-sm font-medium mb-2">{title}:</div>
          <pre className="text-xs bg-muted p-3 rounded-md overflow-x-auto">
            {JSON.stringify(value, null, 2)}
          </pre>
        </div>
      );
    }

    return (
      <div>
        <div className="text-sm font-medium mb-1">{title}:</div>
        <div className="text-sm bg-muted p-2 rounded">
          {String(value)}
        </div>
      </div>
    );
  };

  const filteredDrifts = drifts.filter(drift =>
    filterSeverity === 'all' || drift.severity === filterSeverity
  );

  const driftsByType = drifts.reduce((acc, drift) => {
    if (!acc[drift.type]) acc[drift.type] = [];
    acc[drift.type].push(drift);
    return acc;
  }, {} as Record<string, DriftDiff[]>);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Drift Analysis</h2>
          <p className="text-muted-foreground">
            Compare API specifications with current implementations
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            className="px-3 py-2 border border-input rounded-md bg-background text-sm"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>

          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as 'unified' | 'split')}>
            <TabsList>
              <TabsTrigger value="split">Split View</TabsTrigger>
              <TabsTrigger value="unified">Unified View</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {Object.entries(driftsByType).map(([type, typeDrifts]) => (
          <Card key={type}>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getTypeIcon(type)}
                  <span className="text-sm font-medium capitalize">
                    {type.replace('_', ' ')}
                  </span>
                </div>
                <Badge variant="secondary">
                  {typeDrifts.length}
                </Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Drift List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Detected Drifts ({filteredDrifts.length})</span>
            <div className="text-sm text-muted-foreground">
              {specTitle} vs {implTitle}
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {filteredDrifts.map((drift) => (
              <div key={drift.id} className="border rounded-lg">
                {/* Drift Header */}
                <div
                  className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50"
                  onClick={() => toggleDrift(drift.id)}
                >
                  <div className="flex items-center space-x-3">
                    {expandedDrifts.has(drift.id) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}

                    {getStatusIcon(drift.status)}

                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-medium">{drift.path}</span>
                        <Badge
                          variant="secondary"
                          className={getStatusColor(drift.status)}
                        >
                          {drift.status}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {drift.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-2">
                    <Badge
                      variant="secondary"
                      className={getSeverityColor(drift.severity)}
                    >
                      {drift.severity}
                    </Badge>
                    <Badge variant="outline">
                      {drift.type}
                    </Badge>
                  </div>
                </div>

                {/* Drift Details */}
                {expandedDrifts.has(drift.id) && (
                  <div className="px-4 pb-4 border-t bg-muted/20">
                    <div className="pt-4">
                      {viewMode === 'split' ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <h4 className="font-medium mb-2 text-green-700">
                              {specTitle}
                            </h4>
                            {renderValue(drift.specValue, 'Specification')}
                          </div>
                          <div>
                            <h4 className="font-medium mb-2 text-blue-700">
                              {implTitle}
                            </h4>
                            {renderValue(drift.implValue, 'Implementation')}
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-3">
                          <div className="bg-red-50 border-l-4 border-red-400 p-3">
                            <div className="flex">
                              <Minus className="h-5 w-5 text-red-400" />
                              <div className="ml-3">
                                <p className="text-sm text-red-700">
                                  <strong>Removed from spec:</strong>
                                </p>
                                {renderValue(drift.specValue, '')}
                              </div>
                            </div>
                          </div>

                          <div className="bg-green-50 border-l-4 border-green-400 p-3">
                            <div className="flex">
                              <Plus className="h-5 w-5 text-green-400" />
                              <div className="ml-3">
                                <p className="text-sm text-green-700">
                                  <strong>Added to implementation:</strong>
                                </p>
                                {renderValue(drift.implValue, '')}
                              </div>
                            </div>
                          </div>
                        </div>
                      )}

                      {/* Suggestions */}
                      {drift.suggestions && drift.suggestions.length > 0 && (
                        <div className="mt-4">
                          <h5 className="font-medium mb-2">Suggestions:</h5>
                          <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                            {drift.suggestions.map((suggestion, index) => (
                              <li key={index}>{suggestion}</li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex items-center justify-between mt-4 pt-4 border-t">
                        <div className="text-sm text-muted-foreground">
                          {drift.lineNumber && `Line ${drift.lineNumber}`}
                        </div>

                        <div className="flex items-center space-x-2">
                          {onGenerateFix && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onGenerateFix(drift.id)}
                            >
                              Generate Fix
                            </Button>
                          )}

                          {onAcceptDrift && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onAcceptDrift(drift.id)}
                            >
                              Accept
                            </Button>
                          )}

                          {onIgnoreDrift && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => onIgnoreDrift(drift.id)}
                            >
                              Ignore
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}

            {filteredDrifts.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-500" />
                <p>No drifts detected. Specifications and implementations are in sync!</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
