// AI Documentation Gap Finder - Frontend Types

export type GapType =
  | 'missing'
  | 'partial'
  | 'stale'
  | 'broken_link'
  | 'incorrect_sample'
  | 'orphan_doc'
  | 'outdated_screenshot';

export type GapSeverity = 'low' | 'medium' | 'high' | 'critical';
export type GapStatus = 'open' | 'investigating' | 'resolved' | 'wont_fix';

export interface Gap {
  id: string;
  project_id: string;
  type: GapType;
  entity_id?: string;
  doc_id?: string;
  severity: GapSeverity;
  priority: number;
  reason: string;
  status: GapStatus;
  created_at: string;
  updated_at: string;

  // Related data (populated by API)
  entity?: CodeEntity;
  doc?: DocEntity;
  project?: Project;
}

export interface CodeEntity {
  id: string;
  project_id: string;
  kind: 'function' | 'class' | 'endpoint' | 'cli' | 'flag' | 'env' | 'type';
  name: string;
  path: string;
  lang: string;
  signature?: any;
  visibility: 'public' | 'private' | 'internal';
  version?: string;
  line_start?: number;
  line_end?: number;
  docstring?: string;
  metadata?: any;
}

export interface DocEntity {
  id: string;
  project_id: string;
  path: string;
  title?: string;
  headings: DocHeading[];
  links: DocLink[];
  code_blocks: CodeBlock[];
  frontmatter?: any;
  last_commit?: string;
  last_updated?: string;
  word_count: number;
  metadata?: any;
}

export interface DocHeading {
  level: number;
  text: string;
  anchor: string;
  line_number: number;
}

export interface DocLink {
  text: string;
  url: string;
  line_number: number;
  is_external: boolean;
}

export interface CodeBlock {
  language: string;
  code: string;
  line_number: number;
}

export interface Project {
  id: string;
  org_id: string;
  name: string;
  code_repo?: string;
  docs_repo?: string;
  default_branch: string;
  created_at: string;
  organization?: Organization;
}

export interface Organization {
  id: string;
  name: string;
  plan: 'free' | 'pro' | 'enterprise';
  created_at: string;
}

export interface User {
  id: string;
  email: string;
  role: 'owner' | 'admin' | 'member';
  org_id?: string;
  tz: string;
}

// API Request/Response types
export interface GapFilters {
  project_id?: string;
  type?: GapType[];
  severity?: GapSeverity[];
  status?: GapStatus[];
  assigned_to?: string;
  search?: string;
  sort_by?: 'priority' | 'created_at' | 'severity' | 'type';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    total_pages: number;
  };
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// Component Props Types
export interface GapTableProps {
  gaps: Gap[];
  loading?: boolean;
  onGapSelect?: (gap: Gap) => void;
  onGapUpdate?: (gapId: string, updates: Partial<Gap>) => void;
  filters?: GapFilters;
  onFiltersChange?: (filters: GapFilters) => void;
}

export interface GapCardProps {
  gap: Gap;
  onUpdate?: (updates: Partial<Gap>) => void;
  onAssign?: (userId: string) => void;
  compact?: boolean;
}

export interface FilterPanelProps {
  filters: GapFilters;
  onChange: (filters: GapFilters) => void;
  availableProjects: Project[];
  availableUsers: User[];
}

// Form Types
export interface CreateProjectForm {
  name: string;
  code_repo?: string;
  docs_repo?: string;
  default_branch?: string;
}

// Utility Types
export type SortDirection = 'asc' | 'desc';
export type LoadingState = 'idle' | 'loading' | 'success' | 'error';

// Theme Types
export type Theme = 'light' | 'dark' | 'system';

// Dashboard Types
export interface DashboardStats {
  total_gaps: number;
  open_gaps: number;
  critical_gaps: number;
  resolved_gaps: number;
  gaps_by_type: Record<GapType, number>;
  gaps_by_severity: Record<GapSeverity, number>;
  recent_activity: ActivityItem[];
}

export interface ActivityItem {
  id: string;
  type: 'gap_created' | 'gap_resolved' | 'gap_assigned' | 'project_created';
  description: string;
  timestamp: string;
  user?: User;
  gap?: Gap;
  project?: Project;
}
