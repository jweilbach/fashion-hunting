# Feed Configuration Guide - Marketing Hunting

This guide explains how to configure different feed types in Marketing Hunting to track fashion brands and industry trends.

## Overview

Marketing Hunting supports two main feed providers:
- **RSS Feeds**: Direct RSS feeds or keyword-based Google News searches
- **Google Search**: Web-wide searches using Google Custom Search API

Each provider has different feed types with specific use cases.

---

## RSS Feed Provider

### 1. RSS URL

**What it is**: A direct link to a website's RSS feed.

**When to use**:
- You know a specific publication's RSS feed URL
- You want to monitor ALL content from a particular source
- You prefer comprehensive coverage from trusted sources

**Example usage**:
```
Feed URL: https://www.vogue.com/feed/rss
Result: All articles published by Vogue
```

```
Feed URL: https://wwd.com/feed/
Result: All articles from Women's Wear Daily
```

**Common fashion industry RSS feeds**:
- Vogue: `https://www.vogue.com/feed/rss`
- WWD: `https://wwd.com/feed/`
- Business of Fashion: `https://www.businessoffashion.com/feed/`
- Fashionista: `https://fashionista.com/feed`

**Pros**:
- No API quotas or costs
- Unlimited fetches
- Reliable and fast
- Get ALL content from source

**Cons**:
- Requires knowing the RSS URL
- Not all websites provide RSS feeds
- Less targeted than keyword searches

---

### 2. Keyword (Google News)

**What it is**: Automatically converts a keyword into a Google News RSS feed URL.

**When to use**:
- You want to track mentions of a specific brand across ALL news sources
- You don't want to manually find RSS feeds
- You prefer Google's news aggregation

**How it works**:
When you enter a keyword like `Versace`, the system automatically converts it to:
```
https://news.google.com/rss/search?q=Versace
```

**Example usage**:
```
Keyword: Versace
Result: All Google News articles mentioning "Versace"
```

```
Keyword: "Balenciaga controversy"
Result: News articles about Balenciaga controversies (exact phrase)
```

```
Keyword: Gucci OR Prada OR Fendi
Result: Articles mentioning any of these luxury brands
```

**Advanced search operators**:
- **Exact phrase**: `"luxury fashion week"`
- **OR operator**: `Chanel OR Dior OR Hermès`
- **Exclude term**: `fashion -sustainability`
- **Multiple terms**: `Louis Vuitton collaboration`

**Pros**:
- No API quotas or costs
- Aggregates from thousands of news sources
- Simple keyword-based setup
- Google's news ranking and filtering

**Cons**:
- Limited to Google News sources
- Can't search entire web (blogs, forums, etc.)
- Google News may filter some content

---

## Google Search Provider

Both Google Search feed types use the **Google Custom Search API** to search the entire web (not just news). The distinction between "Brand Search" and "Keyword Search" is organizational to help you categorize your feeds.

### Technical Details (Both Types)

**API**: Google Custom Search API
**Search scope**: Entire web (news, blogs, forums, social media, etc.)
**Quota**: 100 searches/day (free tier)
**Cost**: $5 per 1,000 additional queries
**Rate limit**: Configurable fetch frequency

---

### 1. Brand Search

**What it is**: Web-wide search for a specific fashion brand name.

**When to use**:
- Tracking mentions of a specific brand across the entire internet
- Need more comprehensive coverage than Google News
- Want to catch blog posts, forums, and social media mentions

**Example usage**:
```
Search Query: Versace
Result: All web pages mentioning "Versace" (news, blogs, forums, reviews)
```

```
Search Query: "Michael Kors"
Result: Exact phrase matches across the web
```

```
Search Query: Off-White
Result: Mentions of the Off-White brand
```

**Best practices**:
- Use quotes for multi-word brand names: `"Ralph Lauren"`
- Be specific to avoid false positives: `"Bottega Veneta"` not just `Bottega`
- One brand per feed for better tracking

---

### 2. Keyword Search

**What it is**: Web-wide search for broader industry topics, trends, or themes.

**When to use**:
- Tracking industry trends beyond specific brands
- Researching fashion topics and themes
- Monitoring competitive landscape
- Discovering emerging brands or designers

**Example usage**:
```
Search Query: luxury fashion trends 2025
Result: Articles about upcoming luxury trends
```

```
Search Query: sustainable fashion innovation
Result: Content about sustainability in fashion
```

```
Search Query: Paris Fashion Week highlights
Result: Coverage of fashion week events
```

```
Search Query: Gen Z fashion preferences
Result: Analysis of younger consumer trends
```

**Best practices**:
- Use multi-word phrases for better targeting
- Include year for timely results: `fashion week 2025`
- Combine concepts: `sustainable luxury brands`
- Use specific events: `Met Gala fashion`

---

## Comparison: RSS vs Google Search

| Feature | RSS URL | Keyword (Google News) | Google Search (Both Types) |
|---------|---------|----------------------|---------------------------|
| **Coverage** | Single source | Google News sources | Entire web |
| **Cost** | Free | Free | 100/day free, then $5/1000 |
| **Quota** | Unlimited | Unlimited | 100/day (free tier) |
| **Setup** | Need RSS URL | Just enter keyword | Just enter query |
| **Best for** | Trusted sources | Brand news tracking | Comprehensive monitoring |
| **Speed** | Very fast | Fast | Moderate |

---

## Recommended Feed Strategy

### For Brand Monitoring:
1. **Primary tracking**: RSS Keyword (Google News) for each major brand
   - Example: `Versace`, `Gucci`, `Prada`
2. **Supplemental**: Google Search Brand Search for comprehensive web coverage
   - Use sparingly due to quota limits
3. **Industry sources**: Direct RSS URLs for key publications
   - Vogue, WWD, BoF feeds

### For Industry Trends:
1. **Broad themes**: Google Search Keyword Search
   - Example: `sustainable fashion trends`, `luxury market analysis`
2. **News aggregation**: RSS Keyword (Google News)
   - Example: `fashion technology`, `digital fashion`
3. **Trusted sources**: Direct RSS URLs
   - Industry analyst blogs, research publications

---

## Feed Configuration Tips

### Fetch Frequency
- **High-priority brands**: Every 1-2 hours
- **Industry trends**: Every 6-12 hours
- **General monitoring**: Daily

### Avoiding Quota Issues
- Use RSS feeds (unlimited) for high-frequency monitoring
- Reserve Google Search API for unique needs only
- Monitor "Fetch Success Rate" to identify problematic feeds
- Disable low-value feeds that consume quota

### Organizing Feeds
- Use Brand Search for specific brand names
- Use Keyword Search for topics and trends
- Use descriptive names for easy management
- Group related feeds mentally (the UI shows all feeds together)

---

## Understanding Feed Metrics

### Fetch Success Rate
Located in the Feeds page, this shows:
```
Fetch Success Rate = (Successful fetches / Total fetch attempts) × 100%
```

**What it means**:
- **95-100%**: Feed is reliable
- **80-95%**: Occasional issues (check feed URL)
- **Below 80%**: Feed may be broken or rate-limited

**Note**: This tracks feed fetching reliability, not article processing success.

---

## Troubleshooting

### Feed not returning results
- **RSS URL**: Verify the URL in a browser
- **Keywords**: Try broader or more specific terms
- **Google Search**: Check quota hasn't been exceeded

### Too many irrelevant results
- Use exact phrase matching with quotes: `"Balenciaga"`
- Add negative keywords: `fashion -costume`
- Make queries more specific: `luxury fashion brands` instead of `fashion`

### Feed fetch failures
- Check "Fetch Success Rate" in Feeds page
- Verify RSS URLs are still valid
- Ensure Google API credentials are configured
- Review fetch frequency settings

---

## Examples by Use Case

### Luxury Brand Monitoring
```
Feed Type: RSS Keyword (Google News)
Query: "Louis Vuitton"
Frequency: Every 2 hours
```

### Emerging Designer Discovery
```
Feed Type: Google Search - Keyword Search
Query: emerging fashion designers 2025
Frequency: Daily
```

### Fashion Week Coverage
```
Feed Type: RSS URL
URL: https://wwd.com/feed/
Frequency: Every 4 hours during fashion week season
```

### Sustainability Trends
```
Feed Type: Google Search - Keyword Search
Query: sustainable luxury fashion innovations
Frequency: Every 12 hours
```

### Competitor Analysis
```
Feed Type: Google Search - Brand Search
Query: "Competing Brand Name"
Frequency: Every 6 hours
```

---

## API Quota Management

### Google Custom Search Free Tier
- **100 queries per day** (resets at midnight Pacific Time)
- Each feed fetch = 1 query
- Monitor usage in Google Cloud Console

### Optimizing Quota Usage
1. Use RSS feeds for high-frequency monitoring
2. Set longer intervals for Google Search feeds
3. Disable feeds during testing/development
4. Upgrade to paid tier if needed ($5/1,000 queries)

### Calculating Daily Quota Needs
```
Feeds using Google Search: 5 feeds
Fetch frequency: Every 6 hours = 4 fetches/day per feed
Total daily queries: 5 × 4 = 20 queries/day
Remaining quota: 80 queries/day for other feeds
```

---

## Best Practices Summary

1. **Start with RSS feeds** - They're free, unlimited, and reliable
2. **Use specific queries** - Better targeting = more relevant results
3. **Monitor fetch success rates** - Identify and fix broken feeds
4. **Manage API quota carefully** - Reserve Google Search for unique needs
5. **Set appropriate frequencies** - Balance freshness with resource usage
6. **Test queries before committing** - Try searches manually first
7. **Review results regularly** - Refine queries based on what you find

---

## Getting Help

For questions or issues with feed configuration:
- Review the Reports page to see what's being captured
- Check the History page for feed execution details
- Monitor fetch success rates in the Feeds page
- Adjust queries based on results quality
