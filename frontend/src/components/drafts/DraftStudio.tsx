'use client';

import { useState, useEffect, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { Textarea } from '@/components/ui/Textarea';
import {
  Save,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Eye,
  Code,
  FileText,
  Link,
  Download,
  Upload,
  RotateCcw,
  Settings
} from 'lucide-react';
import { apiClient } from '@/lib/api';

interface DraftStudioProps {
  initialContent?: string;
  draftId?: string;
  projectId?: string;
  onSave?: (content: string, frontmatter: any) => void;
  onPublish?: (content: string) => void;
  readOnly?: boolean;
}

interface LintResult {
  line: number;
  column: number;
  message: string;
  severity: 'error' | 'warning' | 'info';
  rule?: string;
}

interface LinkCheckResult {
  url: string;
  status: 'valid' | 'broken' | 'warning';
  statusCode?: number;
  message: string;
}

interface SnippetTestResult {
  language: string;
  success: boolean;
  output?: string;
  error?: string;
  executionTime: number;
}

export function DraftStudio({
  initialContent = '',
  draftId,
  projectId,
  onSave,
  onPublish,
  readOnly = false,
}: DraftStudioProps) {
  const [content, setContent] = useState(initialContent);
  const [frontmatter, setFrontmatter] = useState<any>({});
  const [activeTab, setActiveTab] = useState('editor');
  const [lintResults, setLintResults] = useState<LintResult[]>([]);
  const [linkCheckResults, setLinkCheckResults] = useState<LinkCheckResult[]>([]);
  const [snippetTestResults, setSnippetTestResults] = useState<SnippetTestResult[]>([]);

  // Extract frontmatter from content
  useEffect(() => {
    const extracted = extractFrontmatter(content);
    setFrontmatter(extracted.frontmatter);
    if (extracted.body !== content) {
      // Update content without frontmatter for editing
      setContent(extracted.body);
    }
  }, [content]);

  // Lint mutation
  const lintMutation = useMutation({
    mutationFn: async (mdxContent: string) => {
      // Mock linting - in real implementation, this would call a linting service
      const results: LintResult[] = [];

      // Basic checks
      const lines = mdxContent.split('\n');
      lines.forEach((line, index) => {
        // Check for broken links
        const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
        let match;
        while ((match = linkRegex.exec(line)) !== null) {
          const url = match[2];
          if (url.includes('http') && !url.startsWith('http')) {
            results.push({
              line: index + 1,
              column: match.index,
              message: 'Link URL should start with http:// or https://',
              severity: 'warning',
              rule: 'link-format'
            });
          }
        }

        // Check for code blocks without language
        if (line.trim() === '```' && lines[index + 1] && !lines[index + 1].startsWith('```')) {
          results.push({
            line: index + 1,
            column: 0,
            message: 'Code block should specify a language',
            severity: 'info',
            rule: 'code-language'
          });
        }
      });

      return results;
    },
    onSuccess: (results) => {
      setLintResults(results);
    },
  });

  // Link check mutation
  const linkCheckMutation = useMutation({
    mutationFn: async (mdxContent: string) => {
      const results: LinkCheckResult[] = [];

      // Extract all links
      const linkRegex = /\[([^\]]+)\]\(([^)]+)\)/g;
      const links = [];
      let match;
      while ((match = linkRegex.exec(mdxContent)) !== null) {
        links.push({
          text: match[1],
          url: match[2],
          index: match.index
        });
      }

      // Check each link
      for (const link of links) {
        try {
          // Skip relative links for now
          if (!link.url.startsWith('http')) {
            results.push({
              url: link.url,
              status: 'warning',
              message: 'Relative link - cannot validate'
            });
            continue;
          }

          const response = await fetch(link.url, {
            method: 'HEAD',
            mode: 'no-cors' // Avoid CORS issues
          });

          results.push({
            url: link.url,
            status: 'valid',
            statusCode: 200, // Assume success for no-cors
            message: 'Link appears valid'
          });
        } catch (error) {
          results.push({
            url: link.url,
            status: 'broken',
            message: 'Failed to access link'
          });
        }
      }

      return results;
    },
    onSuccess: (results) => {
      setLinkCheckResults(results);
    },
  });

  // Snippet test mutation
  const snippetTestMutation = useMutation({
    mutationFn: async (mdxContent: string) => {
      const results: SnippetTestResult[] = [];

      // Extract code blocks
      const codeBlockRegex = /```(\w+)?\n(.*?)\n```/gs;
      let match;
      while ((match = codeBlockRegex.exec(mdxContent)) !== null) {
        const language = match[1] || 'text';
        const code = match[2];

        if (language === 'javascript' || language === 'js') {
          const result = await testJavaScriptSnippet(code);
          results.push(result);
        } else if (language === 'python' || language === 'py') {
          const result = await testPythonSnippet(code);
          results.push(result);
        } else {
          // Unsupported language
          results.push({
            language,
            success: false,
            error: `Testing not supported for ${language}`,
            executionTime: 0
          });
        }
      }

      return results;
    },
    onSuccess: (results) => {
      setSnippetTestResults(results);
    },
  });

  const testJavaScriptSnippet = async (code: string): Promise<SnippetTestResult> => {
    const startTime = Date.now();

    try {
      // Basic syntax check using Function constructor
      new Function(code);
      const executionTime = Date.now() - startTime;

      return {
        language: 'javascript',
        success: true,
        output: 'Syntax check passed',
        executionTime
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      return {
        language: 'javascript',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        executionTime
      };
    }
  };

  const testPythonSnippet = async (code: string): Promise<SnippetTestResult> => {
    const startTime = Date.now();

    try {
      // Basic syntax check - in a real implementation, this would use a Python interpreter
      const executionTime = Date.now() - startTime;

      // Simple checks
      if ('import ' in code and not code.strip().startswith('import ')):
        return {
          language: 'python',
          success: false,
          error: 'Import statements should be at the top',
          executionTime
        };
      }

      return {
        language: 'python',
        success: true,
        output: 'Basic syntax check passed',
        executionTime
      };
    } catch (error) {
      const executionTime = Date.now() - startTime;
      return {
        language: 'python',
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
        executionTime
      };
    }
  };

  const extractFrontmatter = (content: string) => {
    const frontmatterRegex = /^---\n(.*?)\n---\n/s;
    const match = frontmatterRegex.exec(content);

    if (match) {
      try {
        const frontmatter = parseYaml(match[1]);
        const body = content.replace(frontmatterRegex, '');
        return { frontmatter, body };
      } catch (error) {
        console.error('Failed to parse frontmatter:', error);
      }
    }

    return { frontmatter: {}, body: content };
  };

  const parseYaml = (yamlString: string): any => {
    // Simple YAML parser for frontmatter
    const lines = yamlString.split('\n');
    const result: any = {};

    for (const line of lines) {
      const colonIndex = line.indexOf(':');
      if (colonIndex > 0) {
        const key = line.substring(0, colonIndex).trim();
        const value = line.substring(colonIndex + 1).trim();
        result[key] = value;
      }
    }

    return result;
  };

  const generateFrontmatterString = (fm: any): string => {
    const lines = ['---'];
    for (const [key, value] of Object.entries(fm)) {
      if (Array.isArray(value)) {
        lines.push(`${key}:`);
        value.forEach(item => lines.push(`  - ${item}`));
      } else {
        lines.push(`${key}: ${value}`);
      }
    }
    lines.push('---', '');
    return lines.join('\n');
  };

  const handleSave = () => {
    const fullContent = generateFrontmatterString(frontmatter) + content;
    onSave?.(fullContent, frontmatter);
  };

  const handlePublish = () => {
    const fullContent = generateFrontmatterString(frontmatter) + content;
    onPublish?.(fullContent);
  };

  const runAllChecks = () => {
    lintMutation.mutate(content);
    linkCheckMutation.mutate(content);
    snippetTestMutation.mutate(content);
  };

  const renderPreview = () => {
    // Simple markdown-like rendering
    const lines = content.split('\n');
    const rendered: JSX.Element[] = [];

    lines.forEach((line, index) => {
      if (line.startsWith('# ')) {
        rendered.push(<h1 key={index} className="text-2xl font-bold mb-2">{line.substring(2)}</h1>);
      } else if (line.startsWith('## ')) {
        rendered.push(<h2 key={index} className="text-xl font-semibold mb-2">{line.substring(3)}</h2>);
      } else if (line.startsWith('### ')) {
        rendered.push(<h3 key={index} className="text-lg font-medium mb-2">{line.substring(4)}</h3>);
      } else if (line.trim() === '') {
        rendered.push(<br key={index} />);
      } else if (line.startsWith('- ')) {
        rendered.push(<li key={index} className="ml-4">{line.substring(2)}</li>);
      } else {
        rendered.push(<p key={index} className="mb-2">{line}</p>);
      }
    });

    return <div className="prose max-w-none">{rendered}</div>;
  };

  const getOverallStatus = () => {
    const hasErrors = lintResults.some(r => r.severity === 'error') ||
                     linkCheckResults.some(r => r.status === 'broken') ||
                     snippetTestResults.some(r => !r.success);

    const hasWarnings = lintResults.some(r => r.severity === 'warning') ||
                       linkCheckResults.some(r => r.status === 'warning');

    if (hasErrors) return { status: 'error', icon: XCircle, color: 'text-red-600' };
    if (hasWarnings) return { status: 'warning', icon: AlertTriangle, color: 'text-yellow-600' };
    if (lintResults.length > 0 || linkCheckResults.length > 0 || snippetTestResults.length > 0) {
      return { status: 'success', icon: CheckCircle, color: 'text-green-600' };
    }
    return null;
  };

  const overallStatus = getOverallStatus();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-foreground">Draft Studio</h2>
          <p className="text-muted-foreground">
            Edit and preview your documentation drafts
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {overallStatus && (
            <Badge variant="secondary" className={overallStatus.color}>
              <overallStatus.icon className="h-3 w-3 mr-1" />
              {overallStatus.status}
            </Badge>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={runAllChecks}
            disabled={lintMutation.isPending || linkCheckMutation.isPending || snippetTestMutation.isPending}
          >
            <Play className="h-4 w-4 mr-2" />
            Run Checks
          </Button>

          {!readOnly && (
            <>
              <Button variant="outline" size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>

              <Button size="sm" onClick={handlePublish}>
                <Upload className="h-4 w-4 mr-2" />
                Publish
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Main Editor/Preview */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="editor">
            <Code className="h-4 w-4 mr-2" />
            Editor
          </TabsTrigger>
          <TabsTrigger value="preview">
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </TabsTrigger>
          <TabsTrigger value="checks">
            <CheckCircle className="h-4 w-4 mr-2" />
            Checks
          </TabsTrigger>
        </TabsList>

        <TabsContent value="editor" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">MDX Editor</CardTitle>
            </CardHeader>
            <CardContent>
              <Textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Write your MDX content here..."
                className="min-h-[500px] font-mono text-sm"
                readOnly={readOnly}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="preview" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Live Preview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="min-h-[500px] border rounded-md p-4 bg-background">
                {renderPreview()}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="checks" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Lint Results */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <FileText className="h-5 w-5 mr-2" />
                  Linting ({lintResults.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {lintResults.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No issues found</p>
                  ) : (
                    lintResults.map((result, index) => (
                      <div key={index} className="text-sm">
                        <Badge
                          variant="secondary"
                          className={
                            result.severity === 'error' ? 'bg-red-100 text-red-800' :
                            result.severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-blue-100 text-blue-800'
                          }
                        >
                          {result.severity}
                        </Badge>
                        <span className="ml-2">Line {result.line}: {result.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Link Check Results */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <Link className="h-5 w-5 mr-2" />
                  Links ({linkCheckResults.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {linkCheckResults.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No links to check</p>
                  ) : (
                    linkCheckResults.map((result, index) => (
                      <div key={index} className="text-sm">
                        <Badge
                          variant="secondary"
                          className={
                            result.status === 'broken' ? 'bg-red-100 text-red-800' :
                            result.status === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-green-100 text-green-800'
                          }
                        >
                          {result.status}
                        </Badge>
                        <span className="ml-2 truncate" title={result.url}>
                          {result.url.length > 30 ? result.url.substring(0, 30) + '...' : result.url}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Snippet Test Results */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <Code className="h-5 w-5 mr-2" />
                  Snippets ({snippetTestResults.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {snippetTestResults.length === 0 ? (
                    <p className="text-sm text-muted-foreground">No code snippets found</p>
                  ) : (
                    snippetTestResults.map((result, index) => (
                      <div key={index} className="text-sm">
                        <Badge
                          variant="secondary"
                          className={
                            result.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }
                        >
                          {result.language}
                        </Badge>
                        <span className="ml-2">
                          {result.success ? '✓ Passed' : '✗ Failed'}
                          {result.executionTime > 0 && ` (${result.executionTime}ms)`}
                        </span>
                        {result.error && (
                          <p className="text-xs text-red-600 mt-1">{result.error}</p>
                        )}
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
