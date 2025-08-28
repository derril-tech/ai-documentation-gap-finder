import { Suspense } from 'react';
import { DraftStudio } from '@/components/drafts/DraftStudio';
import { LoadingSpinner } from '@/components/ui/LoadingSpinner';

export default function DraftsPage() {
  const handleSave = (content: string, frontmatter: any) => {
    console.log('Saving draft:', { content: content.substring(0, 100) + '...', frontmatter });
    // In a real implementation, this would save to the backend
  };

  const handlePublish = (content: string) => {
    console.log('Publishing draft:', content.substring(0, 100) + '...');
    // In a real implementation, this would publish to the docs repo
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <Suspense fallback={<LoadingSpinner />}>
        <DraftStudio
          initialContent={`---
title: "Sample API Documentation"
description: "Auto-generated API documentation"
sidebar_position: 1
draft_type: "api_reference"
---

# Sample API Documentation

Welcome to the API documentation.

## Getting Started

Here's how to use the API:

\`\`\`javascript
// JavaScript example
const response = await fetch('/api/endpoint', {
  method: 'GET',
  headers: {
    'Authorization': 'Bearer YOUR_API_KEY'
  }
});

const data = await response.json();
console.log(data);
\`\`\`

\`\`\`python
# Python example
import requests

response = requests.get('/api/endpoint', headers={
    'Authorization': 'Bearer YOUR_API_KEY'
})

data = response.json()
print(data)
\`\`\`

## API Reference

### GET /api/endpoint

Retrieve data from the endpoint.

**Parameters:**
- \`id\` (string, required): The resource ID
- \`include\` (string, optional): Additional data to include

**Response:**
\`\`\`json
{
  "success": true,
  "data": {
    "id": "123",
    "name": "Sample Resource"
  }
}
\`\`\`
`}
          onSave={handleSave}
          onPublish={handlePublish}
        />
      </Suspense>
    </div>
  );
}
