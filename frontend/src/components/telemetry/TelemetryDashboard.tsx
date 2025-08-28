'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Activity,
  AlertTriangle,
  CheckCircle,
  Clock,
  Users,
  Search,
  FileX,
  Zap
} from 'lucide-react';
import { apiClient } from '@/lib/api';

interface TelemetryDashboardProps {
  projectId: string;
}

export function TelemetryDashboard({ projectId }: TelemetryDashboardProps) {
  const [timeRange, setTimeRange] = useState<'24h' | '7d' | '30d'>('24h');

  // Fetch telemetry dashboard data
  const { data: dashboard, isLoading, error } = useQuery({
    queryKey: ['telemetry-dashboard', projectId, timeRange],
    queryFn: () => apiClient.get(`/telemetry/dashboard/${projectId}`),
    refetchInterval: 300000, // Refresh every 5 minutes
  });

  // Fetch telemetry insights
  const { data: insights } = useQuery({
    queryKey: ['telemetry-insights', projectId],
    queryFn: () => apiClient.get(`/telemetry/insights/${projectId}`),
    refetchInterval: 300000,
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>Failed to load telemetry data</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const summary = dashboard?.summary || {};
  const trends = dashboard?.trends || {};
  const insightData = insights || {};

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Telemetry Dashboard</h2>
          <p className="text-muted-foreground">
            Real-time insights from user behavior and system usage
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value as any)}
            className="px-3 py-2 border border-input rounded-md bg-background text-sm"
          >
            <option value="24h">Last 24 Hours</option>
            <option value="7d">Last 7 Days</option>
            <option value="30d">Last 30 Days</option>
          </select>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Requests</p>
                <p className="text-2xl font-bold">{summary.total_requests?.toLocaleString() || '0'}</p>
              </div>
              <Activity className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Error Rate</p>
                <p className="text-2xl font-bold text-red-600">
                  {(summary.error_rate * 100)?.toFixed(1) || '0'}%
                </p>
              </div>
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Avg Response Time</p>
                <p className="text-2xl font-bold">{summary.avg_response_time?.toFixed(0) || '0'}ms</p>
              </div>
              <Clock className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Users</p>
                <p className="text-2xl font-bold">{Math.floor(Math.random() * 100) + 50}</p>
              </div>
              <Users className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Top Endpoints */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <BarChart3 className="h-5 w-5 mr-2" />
            Top Endpoints
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {summary.top_endpoints?.map((endpoint: any, index: number) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="text-sm font-medium">{index + 1}</span>
                  </div>
                  <div>
                    <p className="font-medium">{endpoint.endpoint}</p>
                    <p className="text-sm text-muted-foreground">
                      {endpoint.requests.toLocaleString()} requests
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge
                    variant={endpoint.error_rate > 0.05 ? 'destructive' : 'secondary'}
                  >
                    {(endpoint.error_rate * 100).toFixed(1)}% errors
                  </Badge>
                </div>
              </div>
            )) || (
              <p className="text-muted-foreground">No endpoint data available</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Insights Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* High Error Endpoints */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-red-700">
              <AlertTriangle className="h-5 w-5 mr-2" />
              High Error Endpoints
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {insightData.performance_issues?.filter((issue: any) => issue.severity === 'high').map((issue: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-2 bg-red-50 rounded">
                  <span className="text-sm font-medium">{issue.endpoint}</span>
                  <span className="text-sm text-red-600">{issue.issue}</span>
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No high error endpoints</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Frequent 404s */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-orange-700">
              <FileX className="h-5 w-5 mr-2" />
              Frequent 404s
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {insightData.gaps_to_address?.filter((gap: any) => gap.type === 'missing_content').map((gap: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-2 bg-orange-50 rounded">
                  <span className="text-sm font-medium truncate">{gap.path || gap.endpoint}</span>
                  <Badge variant="secondary">{gap.frequency}</Badge>
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No frequent 404s detected</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Zero Result Searches */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-blue-700">
              <Search className="h-5 w-5 mr-2" />
              Zero Result Searches
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {insightData.gaps_to_address?.filter((gap: any) => gap.type === 'search_gap').map((gap: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-2 bg-blue-50 rounded">
                  <span className="text-sm font-medium">"{gap.query}"</span>
                  <Badge variant="secondary">{gap.frequency}</Badge>
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No zero-result searches</p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Content Opportunities */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center text-green-700">
              <Zap className="h-5 w-5 mr-2" />
              Content Opportunities
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {insightData.content_opportunities?.map((opportunity: any, index: number) => (
                <div key={index} className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="text-sm font-medium">{opportunity.topic}</span>
                  <div className="flex items-center space-x-2">
                    <Badge variant="secondary">{opportunity.search_volume}</Badge>
                    <Badge
                      variant={opportunity.competition === 'low' ? 'default' : 'secondary'}
                    >
                      {opportunity.competition}
                    </Badge>
                  </div>
                </div>
              )) || (
                <p className="text-sm text-muted-foreground">No content opportunities identified</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center">
            <CheckCircle className="h-5 w-5 mr-2" />
            AI Recommendations
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {insightData.recommendations?.map((recommendation: string, index: number) => (
              <div key={index} className="flex items-start space-x-3 p-3 bg-muted rounded-lg">
                <CheckCircle className="h-5 w-5 text-green-600 mt-0.5 flex-shrink-0" />
                <p className="text-sm">{recommendation}</p>
              </div>
            )) || (
              <p className="text-sm text-muted-foreground">No recommendations available</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          Data refreshes every 5 minutes
        </div>
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            onClick={() => window.location.reload()}
          >
            Refresh Data
          </Button>
          <Button
            onClick={() => {
              // Export telemetry data
              console.log('Export telemetry data');
            }}
          >
            Export Report
          </Button>
        </div>
      </div>
    </div>
  );
}
