import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { ClientProxy, ClientProxyFactory, Transport } from '@nestjs/microservices';
import { EndpointUsageEvent, Doc404Event, SearchEvent, TelemetryAnalysis } from './telemetry.types';

@Injectable()
export class TelemetryService {
  private natsClient: ClientProxy;

  constructor() {
    // Initialize NATS client for telemetry events
    this.natsClient = ClientProxyFactory.create({
      transport: Transport.NATS,
      options: {
        servers: [process.env.NATS_URL || 'nats://localhost:4222'],
      },
    });
  }

  async onModuleInit() {
    await this.natsClient.connect();
  }

  async onModuleDestroy() {
    await this.natsClient.close();
  }

  // Track API endpoint usage
  async trackEndpointUsage(
    endpoint: string,
    method: string,
    statusCode: number,
    responseTime: number,
    userId?: string,
    orgId?: string,
    requestSize?: number,
    responseSize?: number,
    errorMessage?: string,
    userAgent?: string,
    ipAddress?: string
  ): Promise<void> {
    const event: EndpointUsageEvent = {
      id: this.generateId(),
      project_id: this.extractProjectId(endpoint), // Extract from endpoint or context
      endpoint,
      method,
      status_code: statusCode,
      response_time: responseTime,
      user_agent: userAgent || '',
      ip_address: ipAddress || '',
      timestamp: Date.now(),
      user_id: userId,
      org_id: orgId,
      request_size: requestSize,
      response_size: responseSize,
      error_message: errorMessage,
    };

    await this.natsClient.emit('telemetry.endpoint.usage', event).toPromise();
  }

  // Track documentation 404s
  async trackDoc404(
    requestedPath: string,
    referrer?: string,
    userId?: string,
    orgId?: string,
    userAgent?: string,
    ipAddress?: string,
    queryParams?: Record<string, string[]>
  ): Promise<void> {
    const event: Doc404Event = {
      id: this.generateId(),
      project_id: this.extractProjectId(requestedPath), // Extract from path or context
      requested_path: requestedPath,
      referrer: referrer,
      user_agent: userAgent || '',
      ip_address: ipAddress || '',
      timestamp: Date.now(),
      user_id: userId,
      org_id: orgId,
      query_params: queryParams,
    };

    await this.natsClient.emit('telemetry.doc.404', event).toPromise();
  }

  // Track search queries
  async trackSearchQuery(
    query: string,
    resultsCount: number,
    clickedResult?: string,
    userId?: string,
    orgId?: string,
    userAgent?: string,
    ipAddress?: string,
    sessionId?: string,
    searchType: string = 'documentation',
    filtersApplied?: Record<string, any>
  ): Promise<void> {
    const event: SearchEvent = {
      id: this.generateId(),
      project_id: this.extractProjectIdFromContext(), // Extract from current context
      query,
      results_count: resultsCount,
      clicked_result: clickedResult,
      user_agent: userAgent || '',
      ip_address: ipAddress || '',
      timestamp: Date.now(),
      user_id: userId,
      org_id: orgId,
      session_id: sessionId,
      search_type: searchType,
      filters_applied: filtersApplied,
    };

    await this.natsClient.emit('telemetry.search.query', event).toPromise();
  }

  // Request telemetry analysis
  async requestAnalysis(
    projectId: string,
    analysisType: string = 'comprehensive',
    timeRangeHours: number = 24,
    includeHistorical: boolean = false
  ): Promise<void> {
    const request = {
      project_id: projectId,
      analysis_type: analysisType,
      time_range_hours: timeRangeHours,
      include_historical: includeHistorical,
      request_id: this.generateId(),
    };

    await this.natsClient.emit('telemetry.analysis.request', request).toPromise();
  }

  // Get telemetry analysis results (this would typically be polled or use websockets)
  async getAnalysisResults(requestId: string): Promise<TelemetryAnalysis | null> {
    // In a real implementation, this would query the analysis results
    // For now, return null as results are handled asynchronously
    return null;
  }

  // Utility methods
  private generateId(): string {
    return `tel_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private extractProjectId(endpoint: string): string {
    // Extract project ID from endpoint path or context
    // This is a simplified implementation
    const match = endpoint.match(/\/projects\/([^\/]+)/);
    return match ? match[1] : 'default';
  }

  private extractProjectIdFromContext(): string {
    // Extract project ID from current request context
    // This would typically come from request context or JWT claims
    return 'current-project';
  }

  // Batch operations for better performance
  async trackMultipleEndpointUsage(events: Omit<EndpointUsageEvent, 'id' | 'timestamp'>[]): Promise<void> {
    const eventsWithIds = events.map(event => ({
      ...event,
      id: this.generateId(),
      timestamp: Date.now(),
    }));

    for (const event of eventsWithIds) {
      await this.natsClient.emit('telemetry.endpoint.usage', event).toPromise();
    }
  }

  // Privacy and compliance helpers
  private sanitizeUserData(data: string): string {
    // Remove or hash sensitive information
    if (!data) return '';

    // Remove potential PII patterns
    data = data.replace(/\b\d{3}-\d{2}-\d{4}\b/g, '[SSN]'); // SSN
    data = data.replace(/\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g, '[EMAIL]'); // Email
    data = data.replace(/\b\d{10,}\b/g, '[PHONE]'); // Phone numbers

    return data;
  }

  private shouldTrackRequest(endpoint: string, method: string): boolean {
    // Define which requests to track
    const excludedEndpoints = [
      '/health',
      '/metrics',
      '/favicon.ico',
      '/robots.txt'
    ];

    const excludedMethods = ['OPTIONS', 'HEAD'];

    return !excludedEndpoints.some(excluded => endpoint.includes(excluded)) &&
           !excludedMethods.includes(method);
  }
}
