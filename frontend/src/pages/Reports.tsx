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
  Checkbox,
  Button,
  Menu,
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
  Download as DownloadIcon,
  ViewList as ViewAllIcon,
  AutoAwesome as NewIcon,
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
  const [providerFilter, setProviderFilter] = useState<string>('');
  const [dateFilter, setDateFilter] = useState<string>('all'); // all, today, week, month
  const [page, setPage] = useState(1);
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());

  // State for selection and export
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set());
  const [exportMenuAnchor, setExportMenuAnchor] = useState<null | HTMLElement>(null);

  // Determine the effective provider for filtering
  // If viewing category-level (no providerId), use the providerFilter dropdown
  // If viewing provider-level, use the provider from URL
  const effectiveProviderId = provider?.id || (providerFilter || undefined);

  // Calculate date range based on filter
  const getDateRange = (): { start_date?: string; end_date?: string } => {
    if (dateFilter === 'all') return {};

    const now = new Date();
    let startDate: Date;

    if (dateFilter === 'today') {
      startDate = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    } else if (dateFilter === 'week') {
      startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else if (dateFilter === 'month') {
      startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    } else {
      return {};
    }

    return { start_date: startDate.toISOString() };
  };

  // Build query params
  const queryParams: ReportsQueryParams = useMemo(() => {
    const dateRange = getDateRange();
    return {
      provider: effectiveProviderId,
      source_type: category?.sourceType,
      sentiment: sentimentFilter || undefined,
      brand: brandFilter || undefined,
      search: searchQuery || undefined,
      start_date: dateRange.start_date,
      skip: (page - 1) * ITEMS_PER_PAGE,
      limit: ITEMS_PER_PAGE,
    };
  }, [effectiveProviderId, category?.sourceType, sentimentFilter, brandFilter, searchQuery, dateFilter, page]);

  // Fetch reports - enabled when we have a category
  const { data: reportsData, isLoading, error } = useQuery({
    queryKey: ['reports', queryParams],
    queryFn: () => reportsApi.getReports(queryParams),
    enabled: !!category,
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

  const toggleSelected = (reportId: string) => {
    setSelectedReports(prev => {
      const newSet = new Set(prev);
      if (newSet.has(reportId)) {
        newSet.delete(reportId);
      } else {
        newSet.add(reportId);
      }
      return newSet;
    });
  };

  const selectAllOnPage = () => {
    if (reportsData?.items) {
      setSelectedReports(prev => {
        const newSet = new Set(prev);
        reportsData.items.forEach(r => newSet.add(r.id));
        return newSet;
      });
    }
  };

  const deselectAllOnPage = () => {
    if (reportsData?.items) {
      setSelectedReports(prev => {
        const newSet = new Set(prev);
        reportsData.items.forEach(r => newSet.delete(r.id));
        return newSet;
      });
    }
  };

  const clearAllSelections = () => {
    setSelectedReports(new Set());
  };

  // Check if all items on current page are selected
  const allOnPageSelected = reportsData?.items?.every(r => selectedReports.has(r.id)) ?? false;

  // Count how many items on current page are selected
  const selectedOnPage = reportsData?.items?.filter(r => selectedReports.has(r.id)).length ?? 0;

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
      case 'TikTok':
        return <TikTokIcon />;
      case 'YOUTUBE':
      case 'YouTube':
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
    setPage(1);
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  // Export functions - now using backend API
  const [isExporting, setIsExporting] = useState(false);

  const exportToCSV = async () => {
    if (selectedReports.size === 0) return;
    setIsExporting(true);
    try {
      await reportsApi.exportReports({
        format: 'csv',
        report_ids: Array.from(selectedReports),
      });
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
      setExportMenuAnchor(null);
    }
  };

  const exportToExcel = async () => {
    if (selectedReports.size === 0) return;
    setIsExporting(true);
    try {
      await reportsApi.exportReports({
        format: 'excel',
        report_ids: Array.from(selectedReports),
      });
    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
      setExportMenuAnchor(null);
    }
  };

  // If no category selected, show a message
  if (!category) {
    return (
      <Box>
        <Alert severity="info">
          Please select a category from the sidebar to view reports.
        </Alert>
      </Box>
    );
  }

  // Determine if we're viewing all providers in category or a specific provider
  const isViewingAll = !provider;
  const pageTitle = isViewingAll ? `All ${category.label} Reports` : `${provider.label} Reports`;
  const pageSubtitle = isViewingAll
    ? `Browse and search all ${category.label.toLowerCase()} reports`
    : `${category.label} • Browse and search your ${provider.label} reports`;

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
            {isViewingAll ? <ViewAllIcon /> : provider && <provider.icon />}
          </Avatar>
          <Box>
            <Typography variant="h3" sx={{ fontWeight: 600 }}>
              {pageTitle}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {pageSubtitle}
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
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <FilterIcon color="action" />
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              Filters
            </Typography>
          </Box>

          {/* Export Button */}
          {selectedReports.size > 0 && (
            <Box display="flex" alignItems="center" gap={1}>
              <Typography variant="body2" color="text.secondary">
                {selectedReports.size} selected
              </Typography>
              <Button
                variant="outlined"
                size="small"
                onClick={clearAllSelections}
              >
                Clear All
              </Button>
              <Button
                variant="contained"
                size="small"
                startIcon={isExporting ? <CircularProgress size={16} color="inherit" /> : <DownloadIcon />}
                onClick={(e) => setExportMenuAnchor(e.currentTarget)}
                disabled={isExporting}
              >
                {isExporting ? 'Exporting...' : 'Export'}
              </Button>
              <Menu
                anchorEl={exportMenuAnchor}
                open={Boolean(exportMenuAnchor)}
                onClose={() => setExportMenuAnchor(null)}
              >
                <MenuItem onClick={exportToCSV}>Export as CSV</MenuItem>
                <MenuItem onClick={exportToExcel}>Export as Excel</MenuItem>
              </Menu>
            </Box>
          )}
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

          {/* Provider Filter - only show when viewing all in category */}
          {isViewingAll && (
            <FormControl size="small" sx={{ minWidth: 150 }}>
              <InputLabel>Provider</InputLabel>
              <Select
                value={providerFilter}
                label="Provider"
                onChange={(e) => {
                  setProviderFilter(e.target.value);
                  setPage(1);
                }}
              >
                <MenuItem value="">All Providers</MenuItem>
                {category.providers.map((p) => (
                  <MenuItem key={p.id} value={p.id}>
                    {p.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          )}

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

          {/* Date Range Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Date Range</InputLabel>
            <Select
              value={dateFilter}
              label="Date Range"
              onChange={(e) => {
                setDateFilter(e.target.value);
                setPage(1);
              }}
            >
              <MenuItem value="all">All Time</MenuItem>
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="week">Last 7 Days</MenuItem>
              <MenuItem value="month">Last 30 Days</MenuItem>
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
          {/* Results Count and Select All */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="body2" color="text.secondary">
              Showing {reportsData.items.length} of {reportsData.total} reports
            </Typography>
            {reportsData.items.length > 0 && (
              <Box display="flex" alignItems="center" gap={1}>
                <Button
                  size="small"
                  onClick={allOnPageSelected ? deselectAllOnPage : selectAllOnPage}
                >
                  {allOnPageSelected ? 'Deselect Page' : 'Select Page'}
                </Button>
                {selectedOnPage > 0 && selectedOnPage < reportsData.items.length && (
                  <Typography variant="caption" color="text.secondary">
                    ({selectedOnPage} on this page)
                  </Typography>
                )}
              </Box>
            )}
          </Box>

          {/* No Results */}
          {reportsData.items.length === 0 ? (
            <Card sx={{ p: 6, textAlign: 'center' }}>
              {isViewingAll ? (
                <ViewAllIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
              ) : (
                provider && <provider.icon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
              )}
              <Typography variant="h6" color="text.secondary" gutterBottom>
                No reports found
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {searchQuery || sentimentFilter || brandFilter || providerFilter
                  ? 'Try adjusting your filters to see more results'
                  : `No ${isViewingAll ? category.label.toLowerCase() : provider?.label} reports have been generated yet`}
              </Typography>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {reportsData.items.map((report: Report, index: number) => {
                const isExpanded = expandedReports.has(report.id);
                const isSelected = selectedReports.has(report.id);
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
                      ...(isSelected && {
                        background: alpha(theme.palette.primary.main, 0.05),
                        borderColor: theme.palette.primary.main,
                      }),
                    }}
                  >
                    <CardContent sx={{ p: 3 }}>
                      {/* Main Content */}
                      <Box display="flex" alignItems="flex-start" gap={2}>
                        {/* Checkbox */}
                        <Checkbox
                          checked={isSelected}
                          onChange={() => toggleSelected(report.id)}
                          sx={{ mt: -0.5 }}
                        />

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
                          <Box display="flex" alignItems="flex-start" gap={1}>
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
                            {report.is_new && (
                              <Chip
                                icon={<NewIcon sx={{ fontSize: 14 }} />}
                                label="New!"
                                size="small"
                                sx={{
                                  background: `linear-gradient(135deg, ${theme.palette.warning.main}, ${theme.palette.warning.light})`,
                                  color: theme.palette.warning.contrastText,
                                  fontWeight: 600,
                                  fontSize: '0.7rem',
                                  height: 22,
                                  '& .MuiChip-icon': {
                                    color: theme.palette.warning.contrastText,
                                  },
                                  flexShrink: 0,
                                }}
                              />
                            )}
                          </Box>

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
