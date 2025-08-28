'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';
import {
  AlertTriangle,
  CheckCircle,
  Clock,
  FileText,
  TrendingUp,
  TrendingDown,
  BarChart3
} from 'lucide-react';

export function DashboardStats() {
  const { data: stats, isLoading, error } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => apiClient.get('/stats'), // This would be implemented in the API
    staleTime: 1000 * 60 * 5, // 5 minutes
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-6">
              <LoadingSpinner size="md" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="mb-8">
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>Failed to load dashboard stats</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Mock data for demonstration
  const mockStats = {
    total_gaps: 147,
    open_gaps: 89,
    critical_gaps: 12,
    resolved_gaps: 58,
    gaps_by_type: {
      missing: 45,
      partial: 32,
      stale: 28,
      broken_link: 18,
      incorrect_sample: 15,
      orphan_doc: 7,
      outdated_screenshot: 2,
    },
    gaps_by_severity: {
      critical: 12,
      high: 34,
      medium: 43,
      low: 58,
    },
    recent_activity: [
      { type: 'gap_resolved', description: 'Fixed missing API documentation', timestamp: new Date().toISOString() },
      { type: 'gap_created', description: 'Found stale code examples', timestamp: new Date().toISOString() },
    ],
  };

  const statsData = stats || mockStats;

  const statCards = [
    {
      title: 'Total Gaps',
      value: statsData.total_gaps,
      icon: FileText,
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
    },
    {
      title: 'Open Gaps',
      value: statsData.open_gaps,
      icon: AlertTriangle,
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
    },
    {
      title: 'Critical Gaps',
      value: statsData.critical_gaps,
      icon: AlertTriangle,
      color: 'text-red-600',
      bgColor: 'bg-red-100',
    },
    {
      title: 'Resolved Gaps',
      value: statsData.resolved_gaps,
      icon: CheckCircle,
      color: 'text-green-600',
      bgColor: 'bg-green-100',
    },
  ];

  return (
    <div className="space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat, index) => (
          <Card key={index}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">
                    {stat.title}
                  </p>
                  <p className="text-2xl font-bold">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-full ${stat.bgColor}`}>
                  <stat.icon className={`h-6 w-6 ${stat.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Gaps by Type */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <BarChart3 className="h-5 w-5" />
              <span>Gaps by Type</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(statsData.gaps_by_type).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-sm capitalize">
                    {type.replace('_', ' ')}
                  </span>
                  <div className="flex items-center space-x-2">
                    <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary"
                        style={{
                          width: `${(count / statsData.total_gaps) * 100}%`,
                        }}
                      />
                    </div>
                    <span className="text-sm font-medium w-8 text-right">
                      {count}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Gaps by Severity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5" />
              <span>Gaps by Severity</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(statsData.gaps_by_severity).map(([severity, count]) => {
                const colors = {
                  critical: 'bg-red-500',
                  high: 'bg-orange-500',
                  medium: 'bg-yellow-500',
                  low: 'bg-green-500',
                };

                return (
                  <div key={severity} className="flex items-center justify-between">
                    <span className="text-sm capitalize">{severity}</span>
                    <div className="flex items-center space-x-2">
                      <div className="w-24 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className={`h-full ${colors[severity as keyof typeof colors]}`}
                          style={{
                            width: `${(count / statsData.total_gaps) * 100}%`,
                          }}
                        />
                      </div>
                      <span className="text-sm font-medium w-8 text-right">
                        {count}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Clock className="h-5 w-5" />
            <span>Recent Activity</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {statsData.recent_activity.map((activity, index) => (
              <div key={index} className="flex items-center space-x-3">
                <div className={`p-2 rounded-full ${
                  activity.type === 'gap_resolved'
                    ? 'bg-green-100 text-green-600'
                    : 'bg-blue-100 text-blue-600'
                }`}>
                  {activity.type === 'gap_resolved' ? (
                    <CheckCircle className="h-4 w-4" />
                  ) : (
                    <AlertTriangle className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{activity.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(activity.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Trends */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <TrendingUp className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">Resolution Rate</p>
                <p className="text-2xl font-bold text-green-600">
                  {Math.round((statsData.resolved_gaps / statsData.total_gaps) * 100)}%
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-orange-600" />
              <div>
                <p className="text-sm font-medium">Critical Priority</p>
                <p className="text-2xl font-bold text-orange-600">
                  {statsData.critical_gaps}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center space-x-2">
              <FileText className="h-5 w-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium">Avg. per Project</p>
                <p className="text-2xl font-bold text-blue-600">
                  {Math.round(statsData.total_gaps / 3)} {/* Mock calculation */}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
