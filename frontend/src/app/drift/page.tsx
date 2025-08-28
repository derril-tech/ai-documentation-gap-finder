import { Suspense } from 'react';
import { DriftDiffView } from '@/components/drift/DriftDiffView';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

// Mock data for demonstration
const mockDrifts = [
  {
    id: 'drift_1',
    type: 'endpoint' as const,
    severity: 'high' as const,
    status: 'modified' as const,
    path: '/api/users/{id}',
    specValue: {
      method: 'GET',
      parameters: [
        { name: 'id', type: 'string', required: true },
        { name: 'include', type: 'string', required: false }
      ],
      responses: {
        '200': {
          description: 'User details',
          schema: { type: 'object', properties: { id: { type: 'string' }, name: { type: 'string' } } }
        }
      }
    },
    implValue: {
      method: 'GET',
      parameters: [
        { name: 'id', type: 'string', required: true },
        { name: 'include', type: 'string', required: false },
        { name: 'expand', type: 'string', required: false } // New parameter
      ],
      responses: {
        '200': {
          description: 'User details',
          schema: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              name: { type: 'string' },
              email: { type: 'string' } // New field
            }
          }
        }
      }
    },
    description: 'Implementation has additional parameter and response field not in specification',
    suggestions: [
      'Update API specification to include the new parameter and response field',
      'Document the new functionality in the API documentation',
      'Consider versioning the API for breaking changes'
    ],
    lineNumber: 42
  },
  {
    id: 'drift_2',
    type: 'parameter' as const,
    severity: 'medium' as const,
    status: 'removed' as const,
    path: '/api/posts',
    specValue: {
      name: 'limit',
      type: 'integer',
      required: false,
      description: 'Maximum number of posts to return'
    },
    implValue: null,
    description: 'Required parameter from specification is missing in implementation',
    suggestions: [
      'Add the limit parameter to the implementation',
      'Update the API specification if parameter is no longer needed'
    ],
    lineNumber: 28
  },
  {
    id: 'drift_3',
    type: 'schema' as const,
    severity: 'critical' as const,
    status: 'deprecated' as const,
    path: '/api/legacy-endpoint',
    specValue: {
      deprecated: false,
      description: 'Legacy endpoint for backward compatibility'
    },
    implValue: {
      deprecated: true,
      description: 'This endpoint is deprecated and will be removed'
    },
    description: 'Implementation marks endpoint as deprecated while specification does not',
    suggestions: [
      'Update API specification to mark endpoint as deprecated',
      'Add deprecation notice to API documentation',
      'Plan migration path for clients using this endpoint'
    ],
    lineNumber: 15
  }
];

export default function DriftPage() {
  const handleAcceptDrift = (driftId: string) => {
    console.log('Accepting drift:', driftId);
    // In a real implementation, this would call an API
  };

  const handleIgnoreDrift = (driftId: string) => {
    console.log('Ignoring drift:', driftId);
    // In a real implementation, this would call an API
  };

  const handleGenerateFix = (driftId: string) => {
    console.log('Generating fix for drift:', driftId);
    // In a real implementation, this would call an API
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <Suspense fallback={<LoadingSpinner />}>
        <DriftDiffView
          drifts={mockDrifts}
          specTitle="OpenAPI Specification"
          implTitle="Current Implementation"
          onAcceptDrift={handleAcceptDrift}
          onIgnoreDrift={handleIgnoreDrift}
          onGenerateFix={handleGenerateFix}
        />
      </Suspense>
    </div>
  );
}
