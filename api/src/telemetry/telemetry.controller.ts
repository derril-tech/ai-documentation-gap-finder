import { Controller, Get, Post, Body, Param, Query, UseGuards } from '@nestjs/common';
import { ApiTags, ApiOperation, ApiResponse, ApiBearerAuth } from '@nestjs/swagger';
import { TelemetryService } from './telemetry.service';
import { JwtAuthGuard } from '../auth/guards/jwt-auth.guard';
import {
  TelemetryAnalysisRequest,
  TelemetryAnalysis,
  TelemetryStats,
  TelemetryDashboard
} from './telemetry.types';

@ApiTags('telemetry')
@Controller('telemetry')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class TelemetryController {
  constructor(private readonly telemetryService: TelemetryService) {}

  @Post('analysis')
  @ApiOperation({ summary: 'Request telemetry analysis' })
  @ApiResponse({ status: 200, description: 'Analysis requested successfully' })
  async requestAnalysis(@Body() request: TelemetryAnalysisRequest): Promise<{ request_id: string }> {
    const requestId = `analysis_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    await this.telemetryService.requestAnalysis(
      request.project_id,
      request.analysis_type,
      request.time_range_hours,
      request.include_historical
    );

    return { request_id: requestId };
  }

  @Get('analysis/:requestId')
  @ApiOperation({ summary: 'Get telemetry analysis results' })
  @ApiResponse({ status: 200, description: 'Analysis results retrieved' })
  @ApiResponse({ status: 202, description: 'Analysis still in progress' })
  async getAnalysisResults(@Param('requestId') requestId: string): Promise<TelemetryAnalysis | { status: 'processing' }> {
    const results = await this.telemetryService.getAnalysisResults(requestId);

    if (results) {
      return results;
    }

    // Analysis still in progress
    return { status: 'processing' };
  }

  @Get('dashboard/:projectId')
  @ApiOperation({ summary: 'Get telemetry dashboard data' })
  @ApiResponse({ status: 200, description: 'Dashboard data retrieved' })
  async getDashboard(@Param('projectId') projectId: string): Promise<TelemetryDashboard> {
    // In a real implementation, this would aggregate data from telemetry analysis
    // For now, return mock dashboard data
    return {
      summary: {
        total_requests: 15420,
        error_rate: 0.023,
        avg_response_time: 245,
        top_endpoints: [
          { endpoint: '/api/users', requests: 3240, error_rate: 0.012 },
          { endpoint: '/api/docs', requests: 2890, error_rate: 0.008 },
          { endpoint: '/api/search', requests: 2150, error_rate: 0.045 },
        ],
      },
      insights: {
        high_error_endpoints: ['/api/search', '/api/uploads'],
        frequent_404s: [
          { path: '/docs/legacy-api', count: 45 },
          { path: '/docs/deprecated-endpoint', count: 32 },
        ],
        zero_result_searches: [
          { query: 'websocket configuration', count: 28 },
          { query: 'oauth setup', count: 19 },
        ],
        recommendations: [
          'Add documentation for WebSocket configuration',
          'Create OAuth setup guide',
          'Improve error handling for search endpoints',
        ],
      },
      trends: {
        requests_over_time: Array.from({ length: 24 }, (_, i) => ({
          timestamp: Date.now() - (23 - i) * 3600000,
          requests: Math.floor(Math.random() * 1000) + 500,
          errors: Math.floor(Math.random() * 50) + 10,
        })),
        response_time_trend: Array.from({ length: 24 }, (_, i) => ({
          timestamp: Date.now() - (23 - i) * 3600000,
          avg_response_time: Math.floor(Math.random() * 100) + 200,
        })),
      },
    };
  }

  @Get('stats/:projectId')
  @ApiOperation({ summary: 'Get telemetry statistics' })
  @ApiResponse({ status: 200, description: 'Statistics retrieved' })
  async getStats(@Param('projectId') projectId: string): Promise<TelemetryStats> {
    // Mock statistics - in real implementation, query from telemetry store
    return {
      total_events: 45632,
      endpoint_events: 32145,
      doc_404_events: 8923,
      search_events: 4564,
      analysis_count: 12,
      last_analysis: Date.now() - 3600000, // 1 hour ago
    };
  }

  @Post('track/search')
  @ApiOperation({ summary: 'Track search query (for frontend integration)' })
  @ApiResponse({ status: 200, description: 'Search tracked successfully' })
  async trackSearch(
    @Body() data: {
      query: string;
      results_count: number;
      clicked_result?: string;
      search_type?: string;
      filters_applied?: Record<string, any>;
    }
  ): Promise<{ success: boolean }> {
    await this.telemetryService.trackSearchQuery(
      data.query,
      data.results_count,
      data.clicked_result,
      undefined, // user_id would come from JWT
      undefined, // org_id would come from JWT
      undefined, // user_agent from headers
      undefined, // ip_address from request
      undefined, // session_id
      (data.search_type as any) || 'documentation',
      data.filters_applied
    );

    return { success: true };
  }

  @Get('insights/:projectId')
  @ApiOperation({ summary: 'Get telemetry insights and recommendations' })
  @ApiResponse({ status: 200, description: 'Insights retrieved' })
  async getInsights(@Param('projectId') projectId: string): Promise<{
    gaps_to_address: Array<{
      type: string;
      priority: string;
      description: string;
      impact: number;
    }>;
    content_opportunities: Array<{
      topic: string;
      search_volume: number;
      competition: 'low' | 'medium' | 'high';
    }>;
    performance_issues: Array<{
      endpoint: string;
      issue: string;
      severity: string;
    }>;
  }> {
    // Mock insights based on telemetry data
    return {
      gaps_to_address: [
        {
          type: 'missing_content',
          priority: 'high',
          description: 'WebSocket configuration documentation',
          impact: 85,
        },
        {
          type: 'endpoint_errors',
          priority: 'medium',
          description: 'Search API returning high error rates',
          impact: 67,
        },
        {
          type: 'zero_results',
          priority: 'low',
          description: 'OAuth setup queries with no results',
          impact: 34,
        },
      ],
      content_opportunities: [
        {
          topic: 'WebSocket Configuration',
          search_volume: 28,
          competition: 'low',
        },
        {
          topic: 'OAuth Setup Guide',
          search_volume: 19,
          competition: 'medium',
        },
        {
          topic: 'API Error Handling',
          search_volume: 15,
          competition: 'high',
        },
      ],
      performance_issues: [
        {
          endpoint: '/api/search',
          issue: 'High response time (avg 2.3s)',
          severity: 'high',
        },
        {
          endpoint: '/api/uploads',
          issue: 'Frequent timeouts',
          severity: 'medium',
        },
      ],
    };
  }
}
