import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date): string {
  const d = new Date(date);
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatRelativeTime(date: string | Date): string {
  const d = new Date(date);
  const now = new Date();
  const diffInMs = now.getTime() - d.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

  if (diffInDays === 0) {
    return 'Today';
  } else if (diffInDays === 1) {
    return 'Yesterday';
  } else if (diffInDays < 7) {
    return `${diffInDays} days ago`;
  } else if (diffInDays < 30) {
    const weeks = Math.floor(diffInDays / 7);
    return `${weeks} week${weeks > 1 ? 's' : ''} ago`;
  } else {
    return formatDate(d);
  }
}

export function getSeverityColor(severity: string): string {
  switch (severity.toLowerCase()) {
    case 'critical':
      return 'text-red-600 bg-red-100';
    case 'high':
      return 'text-orange-600 bg-orange-100';
    case 'medium':
      return 'text-yellow-600 bg-yellow-100';
    case 'low':
      return 'text-green-600 bg-green-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case 'open':
      return 'text-blue-600 bg-blue-100';
    case 'investigating':
      return 'text-yellow-600 bg-yellow-100';
    case 'resolved':
      return 'text-green-600 bg-green-100';
    case 'wont_fix':
      return 'text-gray-600 bg-gray-100';
    default:
      return 'text-gray-600 bg-gray-100';
  }
}

export function getTypeColor(type: string): string {
  const colors: Record<string, string> = {
    missing: 'text-red-600 bg-red-100',
    partial: 'text-orange-600 bg-orange-100',
    stale: 'text-yellow-600 bg-yellow-100',
    broken_link: 'text-purple-600 bg-purple-100',
    incorrect_sample: 'text-pink-600 bg-pink-100',
    orphan_doc: 'text-indigo-600 bg-indigo-100',
    outdated_screenshot: 'text-cyan-600 bg-cyan-100',
  };

  return colors[type.toLowerCase()] || 'text-gray-600 bg-gray-100';
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) {
    return text;
  }
  return text.substring(0, maxLength) + '...';
}
