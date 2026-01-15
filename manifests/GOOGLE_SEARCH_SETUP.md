# Google Custom Search API Setup Guide

This guide walks you through setting up Google Custom Search API for the ABMC Phase 1 project.

## Overview

The Google Custom Search API allows you to programmatically search Google and retrieve results. This is useful for monitoring brand mentions and news across the web.

**Pricing:**
- **Free Tier**: 100 queries/day
- **Paid Tier**: $5 per 1,000 queries (up to 10,000 queries/day max)

## Setup Steps

### 1. Enable the Custom Search API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Library**
4. Search for "Custom Search API"
5. Click on it and click **Enable**

### 2. Create API Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **API Key**
3. Copy the API key - you'll need this for your `.env` file
4. (Recommended) Click **Restrict Key** to add application restrictions and API restrictions for security

### 3. Create a Custom Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/)
2. Click **Add** to create a new search engine
3. Configure your search engine:
   - **Sites to search**:
     - Option A: Enter specific sites (e.g., `wwd.com`, `businessoffashion.com`)
     - Option B: Select "Search the entire web" for broader coverage
   - **Name**: Give it a descriptive name (e.g., "Fashion News Search")
4. Click **Create**
5. After creation, click **Control Panel** > **Basics**
6. Copy the **Search engine ID** - you'll need this for your `.env` file

### 4. Configure Environment Variables

Add these variables to your `.env` file:

```bash
# Google Custom Search API Configuration
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_SEARCH_ENGINE_ID=your-search-engine-id-here
```

### 5. Add Google Search Feeds in the Database

In your database, add feed configurations with `provider = 'GOOGLE_SEARCH'`:

```sql
INSERT INTO feed_configs (id, tenant_id, provider, feed_value, enabled, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'your-tenant-id',
    'GOOGLE_SEARCH',
    'Versace news',  -- The search query
    true,
    NOW(),
    NOW()
);
```

**Examples of search queries:**
- `"Versace" news`
- `"Refinery29" latest`
- `"Alison Brod Marketing" announcement`
- `fashion brand launch`

## Usage in Jobs

When configuring a scheduled job, you can control Google Search behavior:

```json
{
  "name": "Daily Fashion News",
  "feed_ids": ["uuid-of-google-search-feed", "uuid-of-rss-feed"],
  "brand_ids": ["brand-uuid-1", "brand-uuid-2"],
  "max_items_per_run": 20,
  "google_search": {
    "results_per_query": 10,
    "date_restrict": "d7"
  }
}
```

**Configuration options:**
- `results_per_query`: Number of results per search query (max 10, default 10)
- `date_restrict`: Time period for results
  - `d1`: Past day
  - `d7`: Past week (default)
  - `m1`: Past month
  - `m6`: Past 6 months
  - `y1`: Past year

## Testing the Provider

You can test the Google Search provider with this Python script:

```python
from providers.google_search_provider import GoogleSearchProvider

# Create provider
provider = GoogleSearchProvider(
    search_queries=["Versace news", "Gucci latest"],
    results_per_query=5,
    date_restrict="d7"
)

# Fetch items
items = provider.fetch_items()

# Print results
for item in items:
    print(f"Title: {item['title']}")
    print(f"Link: {item['link']}")
    print(f"Source: {item['source']}")
    print(f"Query: {item['search_query']}")
    print("---")
```

## Rate Limiting & Best Practices

1. **Monitor your quota**: Check usage in Google Cloud Console
2. **Optimize queries**: Use specific search terms to get better results
3. **Combine with RSS**: Use Google Search for brands/topics without RSS feeds
4. **Schedule wisely**: If on free tier (100/day), spread searches across the day
5. **Example strategy for 100/day limit**:
   - 20 brands × 1 search each = 20 queries
   - Run 4 times per day = 80 queries/day
   - Leaves 20 queries for testing/manual searches

## Troubleshooting

### "Google API key not provided"
- Make sure `GOOGLE_API_KEY` is set in your `.env` file
- Check that the `.env` file is being loaded correctly

### "Google Search Engine ID not provided"
- Make sure `GOOGLE_SEARCH_ENGINE_ID` is set in your `.env` file
- Verify the Search Engine ID is correct (from Programmable Search Engine)

### "Rate limit exceeded" (HTTP 429)
- You've exceeded your daily quota (100 for free tier)
- Wait until the next day or upgrade to paid tier
- Check quota usage in Google Cloud Console

### "Google API client not installed"
- The `google-api-python-client` package is already in `requirements.txt`
- Reinstall dependencies: `pip install -r requirements.txt`

## Provider Architecture

The Google Search provider follows the same pattern as other providers:

```
providers/
├── base_provider.py          # Abstract base class
├── rss_provider.py            # RSS feed provider
└── google_search_provider.py # Google Custom Search provider
```

All providers implement:
- `fetch_items()`: Returns standardized item dicts
- `get_provider_name()`: Returns provider name

This allows the scheduled tasks to handle multiple providers uniformly.
