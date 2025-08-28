// Telemetry Types for AI Documentation Gap Finder

export interface EndpointUsageEvent {
  id: string;
  project_id: string;
  endpoint: string;
  method: string;
  status_code: number;
  response_time: number;
  user_agent: string;
  ip_address: string;
  timestamp: number;
  user_id?: string;
  org_id?: string;
  request_size?: number;
  response_size?: number;
  error_message?: string;
}

export interface Doc404Event {
  id: string;
  project_id: string;
  requested_path: string;
  referrer?: string;
  user_agent: string;
  ip_address: string;
  timestamp: number;
  user_id?: string;
  org_id?: string;
  query_params?: Record<string, string[]>;
  potential_matches?: string[];
}

export interface SearchEvent {
  id: string;
  project_id: string;
  query: string;
  results_count: number;
  clicked_result?: string;
  user_agent: string;
  ip_address: string;
  timestamp: number;
  user_id?: string;
  org_id?: string;
  session_id?: string;
  search_type: 'documentation' | 'api' | 'code';
  filters_applied?: Record<string, any>;
}

export interface TelemetryAnalysis {
  project_id: string;
  period_start: number;
  period_end: number;
  endpoint_usage: Record<string, EndpointUsageStats>;
  doc_404_patterns: Doc404Pattern[];
  search_patterns: SearchPattern[];
  prioritized_gaps: PrioritizedGap[];
  recommendations: string[];
  analysis_timestamp: number;
}

export interface EndpointUsageStats {
  total_requests: number;
  status_counts: Record<string, number>;
  avg_response_time: number;
  error_rate: number;
  p95_response_time: number;
}

export interface Doc404Pattern {
  path: string;
  total_count: number;
  recent_events: Doc404Event[];
  potential_solutions: string[];
}

export interface SearchPattern {
  query: string;
  total_searches: number;
  zero_results: boolean;
  suggested_improvements: string[];
}

export interface PrioritizedGap {
  type: 'endpoint_errors' | 'missing_content' | 'search_gap';
  priority: 'high' | 'medium' | 'low';
  endpoint?: string;
  path?: string;
  query?: string;
  frequency: number;
  error_rate?: number;
  reason: string;
}

// API Request/Response Types
export interface TelemetryAnalysisRequest {
  project_id: string;
  analysis_type?: 'comprehensive' | 'endpoint' | 'search' | '404';
  time_range_hours?: number;
  include_historical?: boolean;
}

export interface TelemetryStats {
  total_events: number;
  endpoint_events: number;
  doc_404_events: number;
  search_events: number;
  analysis_count: number;
  last_analysis?: number;
}

// Dashboard Types
export interface TelemetryDashboard {
  summary: {
    total_requests: number;
    error_rate: number;
    avg_response_time: number;
    top_endpoints: Array<{
      endpoint: string;
      requests: number;
      error_rate: number;
    }>;
  };
  insights: {
    high_error_endpoints: string[];
    frequent_404s: Array<{
      path: string;
      count: number;
    }>;
    zero_result_searches: Array<{
      query: string;
      count: number;
    }>;
    recommendations: string[];
  };
  trends: {
    requests_over_time: Array<{
      timestamp: number;
      requests: number;
      errors: number;
    }>;
    response_time_trend: Array<{
      timestamp: number;
      avg_response_time: number;
    }>;
  };
}
