'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import {
  Copy,
  Download,
  Maximize,
  Minimize,
  Code,
  FileText,
  Eye,
  EyeOff
} from 'lucide-react';

interface SpecViewerProps {
  title: string;
  content: any;
  format?: 'json' | 'yaml';
  showLineNumbers?: boolean;
  highlightLines?: number[];
  diffMode?: boolean;
  addedLines?: number[];
  removedLines?: number[];
  onCopy?: () => void;
  onDownload?: () => void;
}

export function SpecViewer({
  title,
  content,
  format = 'json',
  showLineNumbers = true,
  highlightLines = [],
  diffMode = false,
  addedLines = [],
  removedLines = [],
  onCopy,
  onDownload,
}: SpecViewerProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showRaw, setShowRaw] = useState(false);

  const formatContent = (content: any): string => {
    if (typeof content === 'string') {
      return content;
    }

    if (format === 'json') {
      return JSON.stringify(content, null, 2);
    }

    // For YAML, we'd need a YAML library, but for now we'll use JSON
    return JSON.stringify(content, null, 2);
  };

  const formattedContent = formatContent(content);

  const handleCopy = () => {
    navigator.clipboard.writeText(formattedContent);
    onCopy?.();
  };

  const handleDownload = () => {
    const blob = new Blob([formattedContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title.toLowerCase().replace(/\s+/g, '_')}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    onDownload?.();
  };

  const renderContent = () => {
    const lines = formattedContent.split('\n');

    return (
      <div className="relative">
        <pre className={`text-sm overflow-x-auto ${isExpanded ? 'max-h-none' : 'max-h-96'} ${showRaw ? 'whitespace-pre' : 'whitespace-pre-wrap'}`}>
          <code>
            {lines.map((line, index) => {
              const lineNumber = index + 1;
              const isHighlighted = highlightLines.includes(lineNumber);
              const isAdded = addedLines.includes(lineNumber);
              const isRemoved = removedLines.includes(lineNumber);

              let lineClass = '';
              if (isAdded) lineClass = 'bg-green-100 border-l-4 border-green-500';
              else if (isRemoved) lineClass = 'bg-red-100 border-l-4 border-red-500';
              else if (isHighlighted) lineClass = 'bg-yellow-100';

              return (
                <div
                  key={index}
                  className={`flex ${lineClass} ${isAdded || isRemoved ? 'px-2' : ''}`}
                >
                  {showLineNumbers && (
                    <span className="inline-block w-12 text-right pr-4 text-muted-foreground select-none">
                      {lineNumber}
                    </span>
                  )}
                  <span className="flex-1">
                    {isAdded && <span className="text-green-600 mr-1">+</span>}
                    {isRemoved && <span className="text-red-600 mr-1">-</span>}
                    {line || '\n'}
                  </span>
                </div>
              );
            })}
          </code>
        </pre>

        {!isExpanded && lines.length > 20 && (
          <div className="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-background to-transparent pointer-events-none" />
        )}
      </div>
    );
  };

  return (
    <Card className={isExpanded ? 'fixed inset-4 z-50' : ''}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center space-x-2">
          <Code className="h-5 w-5" />
          <CardTitle className="text-lg">{title}</CardTitle>
          <Badge variant="outline" className="text-xs">
            {format.toUpperCase()}
          </Badge>
          {diffMode && (
            <Badge variant="secondary" className="text-xs">
              Diff View
            </Badge>
          )}
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowRaw(!showRaw)}
            className="h-8 w-8 p-0"
          >
            {showRaw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="h-8 w-8 p-0"
          >
            <Copy className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={handleDownload}
            className="h-8 w-8 p-0"
          >
            <Download className="h-4 w-4" />
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
            className="h-8 w-8 p-0"
          >
            {isExpanded ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {diffMode ? (
          <Tabs defaultValue="unified" className="w-full">
            <TabsList>
              <TabsTrigger value="unified">Unified</TabsTrigger>
              <TabsTrigger value="split">Split</TabsTrigger>
            </TabsList>
            <TabsContent value="unified" className="mt-4">
              {renderContent()}
            </TabsContent>
            <TabsContent value="split" className="mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h4 className="font-medium mb-2 text-red-700">Removed</h4>
                  {renderContent()}
                </div>
                <div>
                  <h4 className="font-medium mb-2 text-green-700">Added</h4>
                  {renderContent()}
                </div>
              </div>
            </TabsContent>
          </Tabs>
        ) : (
          renderContent()
        )}

        {isExpanded && (
          <div className="flex justify-center mt-4">
            <Button
              variant="outline"
              onClick={() => setIsExpanded(false)}
            >
              <Minimize className="h-4 w-4 mr-2" />
              Collapse
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// Utility component for comparing two specs side by side
interface SpecComparisonProps {
  leftTitle: string;
  rightTitle: string;
  leftContent: any;
  rightContent: any;
  format?: 'json' | 'yaml';
}

export function SpecComparison({
  leftTitle,
  rightTitle,
  leftContent,
  rightContent,
  format = 'json'
}: SpecComparisonProps) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <SpecViewer
        title={leftTitle}
        content={leftContent}
        format={format}
      />
      <SpecViewer
        title={rightTitle}
        content={rightContent}
        format={format}
      />
    </div>
  );
}
