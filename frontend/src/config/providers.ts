/**
 * Provider Configuration
 *
 * Central configuration for all media providers and categories.
 * This makes it easy to add new providers or categories without
 * modifying multiple files.
 *
 * To add a new provider:
 * 1. Add the provider to the appropriate category in PROVIDER_CATEGORIES
 * 2. The sidebar and reports page will automatically pick it up
 *
 * To add a new category:
 * 1. Add a new entry to PROVIDER_CATEGORIES with id, label, icon, and providers
 * 2. Update the source_type mapping if needed
 */

import {
  Instagram as InstagramIcon,
  MusicNote as TikTokIcon,
  YouTube as YouTubeIcon,
  Newspaper as NewsIcon,
  RssFeed as RssIcon,
} from '@mui/icons-material';
import type { SvgIconComponent } from '@mui/icons-material';

// Provider definition
export interface Provider {
  id: string;           // Backend provider type (e.g., 'INSTAGRAM')
  label: string;        // Display name (e.g., 'Instagram')
  icon: SvgIconComponent;
  route: string;        // URL route segment (e.g., 'instagram')
}

// Category definition
export interface ProviderCategory {
  id: string;           // Unique category ID
  label: string;        // Display name
  sourceType: string;   // Backend source_type for filtering
  providers: Provider[];
}

/**
 * Provider Categories Configuration
 *
 * Each category maps to a source_type in the backend.
 * Providers within each category share the same source_type.
 */
export const PROVIDER_CATEGORIES: ProviderCategory[] = [
  {
    id: 'social',
    label: 'Social Media',
    sourceType: 'social',
    providers: [
      {
        id: 'INSTAGRAM',
        label: 'Instagram',
        icon: InstagramIcon,
        route: 'instagram',
      },
      {
        id: 'TIKTOK',
        label: 'TikTok',
        icon: TikTokIcon,
        route: 'tiktok',
      },
      {
        id: 'YOUTUBE',
        label: 'YouTube',
        icon: YouTubeIcon,
        route: 'youtube',
      },
      // Future: Twitter/X, Facebook, LinkedIn, etc.
    ],
  },
  {
    id: 'digital',
    label: 'Digital Media',
    sourceType: 'digital',
    providers: [
      {
        id: 'GOOGLE_SEARCH',
        label: 'Google Search',
        icon: NewsIcon,
        route: 'google-search',
      },
      {
        id: 'RSS',
        label: 'RSS Feeds',
        icon: RssIcon,
        route: 'rss',
      },
      // Future: Blogs, Forums, Reviews, etc.
    ],
  },
  // Future category example:
  // {
  //   id: 'broadcast',
  //   label: 'TV/Press',
  //   sourceType: 'broadcast',
  //   providers: [
  //     {
  //       id: 'TV_NEWS',
  //       label: 'TV News',
  //       icon: TvIcon,
  //       route: 'tv-news',
  //     },
  //   ],
  // },
];

/**
 * Helper functions for working with providers
 */

// Get all providers as a flat array
export const getAllProviders = (): Provider[] => {
  return PROVIDER_CATEGORIES.flatMap(category => category.providers);
};

// Get a provider by its ID
export const getProviderById = (providerId: string): Provider | undefined => {
  return getAllProviders().find(p => p.id === providerId);
};

// Get a provider by its route
export const getProviderByRoute = (route: string): Provider | undefined => {
  return getAllProviders().find(p => p.route === route);
};

// Get a category by its ID
export const getCategoryById = (categoryId: string): ProviderCategory | undefined => {
  return PROVIDER_CATEGORIES.find(c => c.id === categoryId);
};

// Get category for a provider
export const getCategoryForProvider = (providerId: string): ProviderCategory | undefined => {
  return PROVIDER_CATEGORIES.find(category =>
    category.providers.some(p => p.id === providerId)
  );
};

// Get provider display name (handles unknown providers gracefully)
export const getProviderLabel = (providerId: string): string => {
  const provider = getProviderById(providerId);
  return provider?.label || providerId;
};

// Build route path for a provider
export const getProviderRoutePath = (categoryId: string, providerRoute: string): string => {
  return `/reports/${categoryId}/${providerRoute}`;
};

// Check if a provider exists
export const isValidProvider = (providerId: string): boolean => {
  return getAllProviders().some(p => p.id === providerId);
};
