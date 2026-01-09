import React, { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import {
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  alpha,
  useTheme,
  Avatar,
  Stack,
  Paper,
  Pagination,
  IconButton,
  Collapse,
  Link,
  Tooltip,
} from '@mui/material';
import {
  Search as SearchIcon,
  OpenInNew as OpenInNewIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  TrendingUp as ReachIcon,
  CalendarToday as DateIcon,
  SentimentSatisfied as PositiveIcon,
  SentimentNeutral as NeutralIcon,
  SentimentDissatisfied as NegativeIcon,
  FilterList as FilterIcon,
  Instagram as InstagramIcon,
  MusicNote as TikTokIcon,
  YouTube as YouTubeIcon,
  Newspaper as NewsIcon,
  RssFeed as RssIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { reportsApi, type ReportsQueryParams } from '../api/reports';
import { brandsApi } from '../api/brands';
import { motion } from 'framer-motion';
import type { Report } from '../types';
import { getCategoryById, getProviderByRoute } from '../config/providers';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const ITEMS_PER_PAGE = 10;

const Reports: React.FC = () => {
  const theme = useTheme();
  const { categoryId, providerId } = useParams<{ categoryId: string; providerId: string }>();

  // Get category and provider info
  const category = categoryId ? getCategoryById(categoryId) : undefined;
  const provider = providerId ? getProviderByRoute(providerId) : undefined;

  // State for filters
  const [searchQuery, setSearchQuery] = useState('');
  const [sentimentFilter, setSentimentFilter] = useState<string>('');
  const [brandFilter, setBrandFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());

  // Build query params
  const queryParams: ReportsQueryParams = useMemo(() => ({
    provider: provider?.id,
    source_type: category?.sourceType,
    sentiment: sentimentFilter || undefined,
    brand: brandFilter || undefined,
    search: searchQuery || undefined,
    skip: (page - 1) * ITEMS_PER_PAGE,
    limit: ITEMS_PER_PAGE,
  }), [provider?.id, category?.sourceType, sentimentFilter, brandFilter, searchQuery, page]);

  // Fetch reports
  const { data: reportsData, isLoading, error } = useQuery({
    queryKey: ['reports', queryParams],
    queryFn: () => reportsApi.getReports(queryParams),
    enabled: !!provider,
  });

  // Fetch brands for filter dropdown
  const { data: brands } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.getBrands(),
  });

  const toggleExpanded = (reportId: string) => {
    setExpandedReports(prev => {
      const newSet = new Set(prev);
      if (newSet.has(reportId)) {
        newSet.delete(reportId);
      } else {
        newSet.add(reportId);
      }
      return newSet;
    });
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return <PositiveIcon />;
      case 'negative':
        return <NegativeIcon />;
      default:
        return <NeutralIcon />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return theme.palette.success.main;
      case 'negative':
        return theme.palette.error.main;
      default:
        return theme.palette.warning.main;
    }
  };

  const getProviderIcon = (providerType: string) => {
    switch (providerType) {
      case 'INSTAGRAM':
        return <InstagramIcon />;
      case 'TIKTOK':
        return <TikTokIcon />;
      case 'YOUTUBE':
        return <YouTubeIcon />;
      case 'GOOGLE_SEARCH':
        return <NewsIcon />;
      case 'RSS':
        return <RssIcon />;
      default:
        return <RssIcon />;
    }
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatReach = (reach: number): string => {
    if (reach >= 1000000) {
      return `${(reach / 1000000).toFixed(1)}M`;
    }
    if (reach >= 1000) {
      return `${(reach / 1000).toFixed(1)}K`;
    }
    return reach.toString();
  };

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setPage(1); // Reset to first page on search
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  // If no provider selected, show a message
  if (!provider || !category) {
    return (
      <Box>
        <Alert severity="info">
          Please select a provider from the sidebar to view reports.
        </Alert>
      </Box>
    );
  }

  const ProviderIcon = provider.icon;

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.light, 0.1)}, ${alpha(theme.palette.secondary.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Box display="flex" alignItems="center" gap={2} mb={1}>
          <Avatar
            sx={{
              width: 48,
              height: 48,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            }}
          >
            <ProviderIcon />
          </Avatar>
          <Box>
            <Typography variant="h3" sx={{ fontWeight: 600 }}>
              {provider.label} Reports
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {category.label} • Browse and search your {provider.label} reports
            </Typography>
          </Box>
        </Box>
      </MotionBox>

      {/* Filters */}
      <Paper
        sx={{
          p: 3,
          mb: 3,
          borderRadius: 2,
          background: alpha(theme.palette.background.paper, 0.8),
        }}
      >
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <FilterIcon color="action" />
          <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
            Filters
          </Typography>
        </Box>
        <Box display="flex" gap={2} flexWrap="wrap">
          {/* Search */}
          <TextField
            placeholder="Search reports..."
            value={searchQuery}
            onChange={handleSearchChange}
            size="small"
            sx={{ minWidth: 250, flex: 1 }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon color="action" />
                  </InputAdornment>
                ),
              },
            }}
          />

          {/* Sentiment Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Sentiment</InputLabel>
            <Select
              value={sentimentFilter}
              label="Sentiment"
              onChange={(e) => {
                setSentimentFilter(e.target.value);
                setPage(1);
              }}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="positive">Positive</MenuItem>
              <MenuItem value="neutral">Neutral</MenuItem>
              <MenuItem value="negative">Negative</MenuItem>
            </Select>
          </FormControl>

          {/* Brand Filter */}
          <FormControl size="small" sx={{ minWidth: 180 }}>
            <InputLabel>Brand</InputLabel>
            <Select
              value={brandFilter}
              label="Brand"
              onChange={(e) => {
                setBrandFilter(e.target.value);
                setPage(1);
              }}
            >
              <MenuItem value="">All Brands</MenuItem>
              {brands?.map((brand) => (
                <MenuItem key={brand.id} value={brand.brand_name}>
                  {brand.brand_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>
      </Paper>

      {/* Loading State */}
      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="30vh">
          <CircularProgress />
        </Box>
      )}

      {/* Error State */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          Failed to load reports. Please try again later.
        </Alert>
      )}

      {/* Reports List */}
      {!isLoading && !error && reportsData && (
        <>
          {/* Results Count */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="body2" color="text.secondary">
              Showing {reportsData.items.length} of {reportsData.total} reports
            </Typography>
          </Box>

          {/* No Results */}
          {reportsData.items.length === 0 ? (
            <Card sx={{ p: 6, textAlign: 'center' }}>
              <ProviderIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No reports found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {searchQuery || sentimentFilter || brandFilter
                  ? 'Try adjusting your filters to see more results'
                  : `No ${provider.label} reports have been generated yet`}
              </Typography>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {reportsData.items.map((report: Report, index: number) => {
                const isExpanded = expandedReports.has(report.id);
                const sentimentColor = getSentimentColor(report.sentiment);

                return (
                  <MotionCard
                    key={report.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                    sx={{
                      '&:hover': {
                        transform: 'translateY(-2px)',
                        boxShadow: `0 8px 24px ${alpha(theme.palette.primary.main, 0.15)}`,
                      },
                      transition: 'all 0.3s ease',
                      borderLeft: `4px solid ${sentimentColor}`,
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      {/* Main Content */}
                      <Box display="flex" alignItems="flex-start" gap={2}>
                        {/* Provider Icon */}
                        <Avatar
                          sx={{
                            width: 48,
                            height: 48,
                            background: `linear-gradient(135deg, ${sentimentColor}, ${alpha(sentimentColor, 0.7)})`,
                          }}
                        >
                          {getProviderIcon(report.provider)}
                        </Avatar>

                        {/* Content */}
                        <Box flex={1} minWidth={0}>
                          {/* Title */}
                          <Typography
                            variant="h6"
                            sx={{
                              fontWeight: 600,
                              mb: 1,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: isExpanded ? 'unset' : 2,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {report.title}
                          </Typography>

                          {/* Meta Info */}
                          <Stack direction="row" spacing={2} mb={1.5} flexWrap="wrap" useFlexGap>
                            {/* Date */}
                            <Box display="flex" alignItems="center" gap={0.5}>
                              <DateIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                              <Typography variant="caption" color="text.secondary">
                                {formatDate(report.timestamp)}
                              </Typography>
                            </Box>

                            {/* Reach */}
                            <Box display="flex" alignItems="center" gap={0.5}>
                              <ReachIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                              <Typography variant="caption" color="text.secondary">
                                {formatReach(report.est_reach)} reach
                              </Typography>
                            </Box>

                            {/* Source */}
                            <Typography variant="caption" color="text.secondary">
                              {report.source}
                            </Typography>
                          </Stack>

                          {/* Summary */}
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              mb: 2,
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: isExpanded ? 'unset' : 3,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {report.summary}
                          </Typography>

                          {/* Tags */}
                          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                            {/* Sentiment */}
                            <Chip
                              icon={getSentimentIcon(report.sentiment)}
                              label={report.sentiment.charAt(0).toUpperCase() + report.sentiment.slice(1)}
                              size="small"
                              sx={{
                                backgroundColor: alpha(sentimentColor, 0.1),
                                color: sentimentColor,
                                fontWeight: 500,
                                '& .MuiChip-icon': {
                                  color: sentimentColor,
                                },
                              }}
                            />

                            {/* Topic */}
                            <Chip
                              label={report.topic}
                              size="small"
                              sx={{
                                backgroundColor: alpha(theme.palette.primary.main, 0.1),
                                color: theme.palette.primary.main,
                                fontWeight: 500,
                              }}
                            />

                            {/* Brands */}
                            {report.brands.slice(0, 3).map((brand) => (
                              <Chip
                                key={brand}
                                label={brand}
                                size="small"
                                variant="outlined"
                                sx={{ fontWeight: 500 }}
                              />
                            ))}
                            {report.brands.length > 3 && (
                              <Chip
                                label={`+${report.brands.length - 3} more`}
                                size="small"
                                variant="outlined"
                                sx={{ fontWeight: 500 }}
                              />
                            )}
                          </Stack>

                          {/* Expanded Content */}
                          <Collapse in={isExpanded}>
                            <Box sx={{ mt: 2, pt: 2, borderTop: `1px solid ${theme.palette.divider}` }}>
                              {report.full_text && (
                                <>
                                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                                    Full Content
                                  </Typography>
                                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                    {report.full_text}
                                  </Typography>
                                </>
                              )}

                              {report.brands.length > 0 && (
                                <>
                                  <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                                    All Brands Mentioned
                                  </Typography>
                                  <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ mb: 2 }}>
                                    {report.brands.map((brand) => (
                                      <Chip
                                        key={brand}
                                        label={brand}
                                        size="small"
                                        variant="outlined"
                                        sx={{ fontWeight: 500 }}
                                      />
                                    ))}
                                  </Stack>
                                </>
                              )}

                              <Link
                                href={report.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                sx={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 0.5,
                                  textDecoration: 'none',
                                  '&:hover': {
                                    textDecoration: 'underline',
                                  },
                                }}
                              >
                                View Original Source
                                <OpenInNewIcon sx={{ fontSize: 16 }} />
                              </Link>
                            </Box>
                          </Collapse>
                        </Box>

                        {/* Actions */}
                        <Box display="flex" flexDirection="column" alignItems="center" gap={1}>
                          <Tooltip title={isExpanded ? 'Collapse' : 'Expand'}>
                            <IconButton
                              onClick={() => toggleExpanded(report.id)}
                              size="small"
                              sx={{
                                border: `1px solid ${theme.palette.divider}`,
                                borderRadius: 1,
                              }}
                            >
                              {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Open Link">
                            <IconButton
                              component="a"
                              href={report.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              size="small"
                              sx={{
                                border: `1px solid ${theme.palette.divider}`,
                                borderRadius: 1,
                              }}
                            >
                              <OpenInNewIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>
                    </CardContent>
                  </MotionCard>
                );
              })}
            </Box>
          )}

          {/* Pagination */}
          {reportsData.total > ITEMS_PER_PAGE && (
            <Box display="flex" justifyContent="center" mt={4}>
              <Pagination
                count={Math.ceil(reportsData.total / ITEMS_PER_PAGE)}
                page={page}
                onChange={handlePageChange}
                color="primary"
                size="large"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </>
      )}
    </Box>
  );
};

export default Reports;
