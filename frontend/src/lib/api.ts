// AI Documentation Gap Finder - API Client

import {
  Gap,
  Project,
  Organization,
  User,
  GapFilters,
  PaginatedResponse,
  ApiResponse,
  CreateProjectForm
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:4000/v1';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

class ApiClient {
  private baseURL: string;
  private token: string | null = null;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
          response.status,
          errorData.message || `HTTP ${response.status}: ${response.statusText}`
        );
      }

      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }

      // Network or other error
      throw new ApiError(0, error instanceof Error ? error.message : 'Network error');
    }
  }

  private async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  private async post<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async put<T>(endpoint: string, data?: any): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  private async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }

  // Authentication
  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('auth_token', token);
      } else {
        localStorage.removeItem('auth_token');
      }
    }
  }

  async login(email: string, password: string): Promise<{ access_token: string; user: User }> {
    const response = await this.post('/auth/login', { email, password });
    const { access_token, user } = response;
    this.setToken(access_token);
    return { access_token, user };
  }

  async getCurrentUser(): Promise<User> {
    return this.get('/auth/me');
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  // Organizations
  async getOrganizations(): Promise<Organization[]> {
    return this.get('/organizations');
  }

  async getOrganization(id: string): Promise<Organization> {
    return this.get(`/organizations/${id}`);
  }

  async createOrganization(data: { name: string; plan?: string }): Promise<Organization> {
    return this.post('/organizations', data);
  }

  async updateOrganization(id: string, data: Partial<Organization>): Promise<Organization> {
    return this.put(`/organizations/${id}`, data);
  }

  async deleteOrganization(id: string): Promise<void> {
    return this.delete(`/organizations/${id}`);
  }

  // Projects
  async getProjects(): Promise<Project[]> {
    return this.get('/projects');
  }

  async getProject(id: string): Promise<Project> {
    return this.get(`/projects/${id}`);
  }

  async getProjectsByOrg(orgId: string): Promise<Project[]> {
    return this.get(`/projects/org/${orgId}`);
  }

  async createProject(data: CreateProjectForm): Promise<Project> {
    return this.post('/projects', data);
  }

  async updateProject(id: string, data: Partial<CreateProjectForm>): Promise<Project> {
    return this.put(`/projects/${id}`, data);
  }

  async deleteProject(id: string): Promise<void> {
    return this.delete(`/projects/${id}`);
  }

  // Gaps
  async getGaps(filters: GapFilters = {}): Promise<PaginatedResponse<Gap>> {
    const params = new URLSearchParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        if (Array.isArray(value)) {
          value.forEach(v => params.append(key, v));
        } else {
          params.append(key, String(value));
        }
      }
    });

    return this.get(`/gaps?${params.toString()}`);
  }

  async getGap(id: string): Promise<Gap> {
    return this.get(`/gaps/${id}`);
  }

  async updateGap(id: string, updates: Partial<Gap>): Promise<Gap> {
    return this.put(`/gaps/${id}`, updates);
  }

  async assignGap(id: string, userId: string): Promise<Gap> {
    return this.post(`/gaps/${id}/assign`, { user_id: userId });
  }

  // Scan Operations
  async startProjectScan(projectId: string, mode: 'full' | 'delta' = 'full'): Promise<{ scan_id: string }> {
    return this.post(`/projects/${projectId}/scan`, { mode });
  }

  // Dashboard Stats
  async getDashboardStats(projectId?: string): Promise<{
    total_gaps: number;
    open_gaps: number;
    critical_gaps: number;
    resolved_gaps: number;
    gaps_by_type: Record<string, number>;
    gaps_by_severity: Record<string, number>;
    recent_activity: any[];
  }> {
    const endpoint = projectId ? `/projects/${projectId}/stats` : '/stats';
    return this.get(endpoint);
  }

  // Bulk Operations
  async bulkUpdateGaps(gapIds: string[], updates: Partial<Gap>): Promise<Gap[]> {
    return this.post('/gaps/bulk', { gap_ids: gapIds, updates });
  }

  async bulkAssignGaps(gapIds: string[], userId: string): Promise<Gap[]> {
    return this.post('/gaps/bulk/assign', { gap_ids: gapIds, user_id: userId });
  }

  // Export Operations
  async exportGaps(projectId: string, format: 'json' | 'csv' = 'json'): Promise<Blob> {
    const response = await fetch(`${this.baseURL}/projects/${projectId}/export?format=${format}`, {
      headers: {
        Authorization: this.token ? `Bearer ${this.token}` : '',
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, 'Export failed');
    }

    return response.blob();
  }

  // Error handling
  isApiError(error: any): error is ApiError {
    return error instanceof ApiError;
  }

  getErrorMessage(error: any): string {
    if (this.isApiError(error)) {
      return error.message;
    }
    return 'An unexpected error occurred';
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types
export type { ApiError };
export default apiClient;
