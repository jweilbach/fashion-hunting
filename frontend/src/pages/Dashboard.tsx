import React, { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  Paper,
  List,
  ListItem,
  ListItemText,
  Button,
  Collapse,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Pagination,
  Checkbox,
  Link,
  Avatar,
  Stack,
  alpha,
  useTheme,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Delete as DeleteIcon,
  TrendingUp as TrendingUpIcon,
  Assessment as AssessmentIcon,
  Business as BusinessIcon,
  RssFeed as FeedIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { reportsApi } from '../api/reports';
import { brandsApi } from '../api/brands';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Dashboard: React.FC = () => {
  const theme = useTheme();
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());
  const [reportsPageSize, setReportsPageSize] = useState<number>(10);
  const [brandsPageSize, setBrandsPageSize] = useState<number>(10);
  const [reportsPage, setReportsPage] = useState<number>(1);
  const [brandsPage, setBrandsPage] = useState<number>(1);
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  // Check if any job executions are running to determine refresh interval
  const { data: executions } = useQuery({
    queryKey: ['executions'],
    queryFn: async () => {
      const { jobsApi } = await import('../api/jobs');
      return jobsApi.getAllExecutions(10); // Check last 10 executions
    },
    refetchInterval: 5000, // Check every 5 seconds for running jobs
  });

  const hasRunningJobs = executions?.some(execution => execution.status === 'running') || false;

  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: () => analyticsApi.getOverview(),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  const { data: reportsData, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', 'recent', reportsPageSize, reportsPage],
    queryFn: () => reportsApi.getRecentReports(reportsPageSize, (reportsPage - 1) * reportsPageSize),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  const { data: topBrands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands', 'top', brandsPageSize, brandsPage],
    queryFn: () => brandsApi.getTopBrands(brandsPageSize, (brandsPage - 1) * brandsPageSize),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  // Generate mock chart data from recent reports
  const getChartData = () => {
    if (!reportsData?.items || reportsData.items.length === 0) return [];

    // Group reports by date
    const dateCounts: Record<string, number> = {};
    reportsData.items.forEach((report) => {
      const date = new Date(report.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      dateCounts[date] = (dateCounts[date] || 0) + 1;
    });

    return Object.entries(dateCounts)
      .map(([date, count]) => ({ date, mentions: count }))
      .slice(0, 7)
      .reverse();
  };

  const toggleReportExpansion = (reportId: string) => {
    setExpandedReports((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(reportId)) {
        newSet.delete(reportId);
      } else {
        newSet.add(reportId);
      }
      return newSet;
    });
  };

  const toggleReportSelection = (reportId: string) => {
    setSelectedReports((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(reportId)) {
        newSet.delete(reportId);
      } else {
        newSet.add(reportId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedReports.size === reportsData?.items?.length && reportsData?.items?.length > 0) {
      setSelectedReports(new Set());
    } else {
      setSelectedReports(new Set(reportsData?.items?.map(r => r.id) || []));
    }
  };

  const deleteMutation = useMutation({
    mutationFn: async (reportIds: string[]) => {
      await Promise.all(reportIds.map(id => reportsApi.deleteReport(id)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
      setSelectedReports(new Set());
    },
  });

  const handleDeleteSelected = () => {
    if (selectedReports.size > 0 && window.confirm(`Delete ${selectedReports.size} report(s)?`)) {
      deleteMutation.mutate(Array.from(selectedReports));
    }
  };

  const knownBrandNames = new Set(topBrands?.items?.map(brand => brand.brand_name) || []);

  const sortBrands = (brands: string[]) => {
    const known = brands.filter(brand => knownBrandNames.has(brand));
    const unknown = brands.filter(brand => !knownBrandNames.has(brand));
    return [...known, ...unknown];
  };

  if (analyticsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (analyticsError) {
    return (
      <Alert severity="error">
        Failed to load analytics data. Please try again later.
      </Alert>
    );
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case 'positive':
        return 'success';
      case 'negative':
        return 'error';
      default:
        return 'default';
    }
  };

  const statCards = [
    {
      title: 'Total Mentions',
      value: analytics?.total_reports ?? 0,
      icon: AssessmentIcon,
      color: theme.palette.primary.main,
      gradient: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
    },
    {
      title: 'Brands Tracked',
      value: analytics?.total_brands ?? 0,
      icon: BusinessIcon,
      color: theme.palette.secondary.main,
      gradient: `linear-gradient(135deg, ${theme.palette.secondary.main}, ${theme.palette.info.main})`,
    },
    {
      title: 'Active Feeds',
      value: analytics?.active_feeds ?? 0,
      icon: FeedIcon,
      color: theme.palette.success.main,
      gradient: `linear-gradient(135deg, ${theme.palette.success.main}, ${theme.palette.success.light})`,
    },
  ];

  const chartData = getChartData();

  return (
    <Box>
      {/* Header with gradient background */}
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
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 600 }}>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome back! Here's your media tracking overview.
        </Typography>
      </MotionBox>

      {/* Stats Cards */}
      <Box sx={{ display: 'flex', gap: 3, mb: 4, flexWrap: 'wrap' }}>
        {statCards.map((stat, index) => (
          <Box key={stat.title} sx={{ flex: { xs: '1 1 100%', sm: '1 1 calc(50% - 12px)', md: '1 1 calc(33.333% - 16px)' }, minWidth: 0 }}>
            <MotionCard
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              sx={{
                position: 'relative',
                overflow: 'visible',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  transition: 'all 0.3s ease',
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="center" justifyContent="space-between">
                  <Box>
                    <Typography color="text.secondary" variant="body2" gutterBottom sx={{ fontWeight: 500 }}>
                      {stat.title}
                    </Typography>
                    <Typography variant="h3" sx={{ fontWeight: 700, background: stat.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                      {stat.value.toLocaleString()}
                    </Typography>
                  </Box>
                  <Avatar
                    sx={{
                      width: 64,
                      height: 64,
                      background: stat.gradient,
                      boxShadow: `0 4px 20px ${alpha(stat.color, 0.3)}`,
                    }}
                  >
                    <stat.icon sx={{ fontSize: 32 }} />
                  </Avatar>
                </Box>
              </CardContent>
            </MotionCard>
          </Box>
        ))}
      </Box>

      {/* Chart Section */}
      {chartData.length > 0 && (
        <MotionCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          sx={{ mb: 4 }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" mb={3}>
              <TrendingUpIcon sx={{ mr: 1, color: theme.palette.primary.main }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                Recent Activity
              </Typography>
            </Box>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorMentions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={theme.palette.primary.main} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={theme.palette.primary.main} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke={theme.palette.divider} />
                <XAxis dataKey="date" stroke={theme.palette.text.secondary} style={{ fontSize: '12px' }} />
                <YAxis stroke={theme.palette.text.secondary} style={{ fontSize: '12px' }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: theme.palette.background.paper,
                    border: `1px solid ${theme.palette.divider}`,
                    borderRadius: theme.shape.borderRadius,
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="mentions"
                  stroke={theme.palette.primary.main}
                  strokeWidth={3}
                  fill="url(#colorMentions)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </MotionCard>
      )}

      {/* Recent Reports */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        sx={{ mb: 4 }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                Recent Mentions
              </Typography>
              {selectedReports.size > 0 && (
                <Button
                  variant="contained"
                  color="error"
                  size="small"
                  startIcon={<DeleteIcon />}
                  onClick={handleDeleteSelected}
                  disabled={deleteMutation.isPending}
                >
                  Delete ({selectedReports.size})
                </Button>
              )}
            </Box>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Show</InputLabel>
              <Select
                value={reportsPageSize}
                label="Show"
                onChange={(e) => {
                  setReportsPageSize(Number(e.target.value));
                  setReportsPage(1);
                  setSelectedReports(new Set());
                }}
              >
                <MenuItem value={5}>5</MenuItem>
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
                <MenuItem value={50}>50</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {reportsData && reportsData.items && reportsData.items.length > 0 && (
            <Box display="flex" alignItems="center" mb={2}>
              <Checkbox
                checked={selectedReports.size === reportsData.items.length && reportsData.items.length > 0}
                indeterminate={selectedReports.size > 0 && selectedReports.size < reportsData.items.length}
                onChange={toggleSelectAll}
                size="small"
              />
              <Typography variant="body2" color="text.secondary">
                Select All
              </Typography>
            </Box>
          )}

          {reportsLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <List sx={{ p: 0 }}>
              {reportsData?.items?.map((report, index) => {
                const isExpanded = expandedReports.has(report.id);
                const isSelected = selectedReports.has(report.id);
                return (
                  <motion.div
                    key={report.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                  >
                    <ListItem
                      sx={{
                        borderLeft: `4px solid ${theme.palette.primary.main}`,
                        borderRadius: 2,
                        mb: 2,
                        backgroundColor: isSelected ? alpha(theme.palette.primary.main, 0.05) : 'transparent',
                        transition: 'all 0.2s',
                        '&:hover': {
                          backgroundColor: alpha(theme.palette.primary.main, 0.08),
                        },
                      }}
                    >
                      <Box display="flex" alignItems="flex-start" width="100%">
                        <Checkbox
                          checked={isSelected}
                          onChange={() => toggleReportSelection(report.id)}
                          size="small"
                          sx={{ mt: 0.5, mr: 1 }}
                        />
                        <Box flex={1}>
                          <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                            <Link
                              href={report.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              underline="hover"
                              color="inherit"
                              sx={{ fontWeight: 600, fontSize: '1.05rem' }}
                            >
                              {report.title}
                            </Link>
                            <Chip
                              label={report.sentiment}
                              color={getSentimentColor(report.sentiment)}
                              size="small"
                              sx={{ fontWeight: 500 }}
                            />
                          </Box>

                          <Stack direction="row" spacing={2} mb={1.5} alignItems="center" flexWrap="wrap">
                            <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <TimeIcon sx={{ fontSize: 16 }} />
                              Published: {new Date(report.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </Typography>
                            <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              •
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              Found: {new Date(report.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                            </Typography>
                            <Chip label={report.source} size="small" variant="outlined" />
                          </Stack>

                          {report.brands && report.brands.length > 0 && (
                            <Box mb={1.5}>
                              <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 600 }}>
                                Brands Mentioned:
                              </Typography>
                              {sortBrands(report.brands).map((brand, idx) => {
                                const isKnown = knownBrandNames.has(brand);
                                return (
                                  <Chip
                                    key={idx}
                                    label={brand}
                                    size="small"
                                    variant={isKnown ? 'filled' : 'outlined'}
                                    color={isKnown ? 'success' : 'default'}
                                    sx={{
                                      mr: 0.5,
                                      mb: 0.5,
                                      fontWeight: isKnown ? 600 : 400,
                                    }}
                                  />
                                );
                              })}
                            </Box>
                          )}

                          {report.summary && (
                            <Box>
                              <Collapse in={isExpanded} collapsedSize={60}>
                                <Paper
                                  elevation={0}
                                  sx={{
                                    backgroundColor: alpha(theme.palette.primary.light, 0.08),
                                    p: 2,
                                    borderRadius: 2,
                                  }}
                                >
                                  <Typography variant="body2" color="text.secondary">
                                    {report.summary}
                                  </Typography>
                                </Paper>
                              </Collapse>
                              <Button
                                size="small"
                                onClick={() => toggleReportExpansion(report.id)}
                                sx={{ mt: 1 }}
                                endIcon={
                                  <ExpandMoreIcon
                                    sx={{
                                      transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                      transition: 'transform 0.3s',
                                    }}
                                  />
                                }
                              >
                                {isExpanded ? 'Show Less' : 'Read More'}
                              </Button>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    </ListItem>
                  </motion.div>
                );
              })}
            </List>
          )}

          {reportsData && reportsData.total > reportsPageSize && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={Math.ceil(reportsData.total / reportsPageSize)}
                page={reportsPage}
                onChange={(_, page) => {
                  setReportsPage(page);
                  setExpandedReports(new Set());
                  setSelectedReports(new Set());
                }}
                color="primary"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </CardContent>
      </MotionCard>

      {/* Top Brands */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.5 }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
            <Box display="flex" alignItems="center">
              <BusinessIcon sx={{ mr: 1, color: theme.palette.secondary.main }} />
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                Top Brands
              </Typography>
            </Box>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Show</InputLabel>
              <Select
                value={brandsPageSize}
                label="Show"
                onChange={(e) => {
                  setBrandsPageSize(Number(e.target.value));
                  setBrandsPage(1);
                }}
              >
                <MenuItem value={5}>5</MenuItem>
                <MenuItem value={10}>10</MenuItem>
                <MenuItem value={20}>20</MenuItem>
                <MenuItem value={50}>50</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {brandsLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <List sx={{ p: 0 }}>
              {topBrands?.items?.map((brand, index) => (
                <motion.div
                  key={brand.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <ListItem
                    sx={{
                      borderRadius: 2,
                      mb: 1.5,
                      backgroundColor: alpha(theme.palette.secondary.light, 0.05),
                      transition: 'all 0.2s',
                      '&:hover': {
                        backgroundColor: alpha(theme.palette.secondary.light, 0.12),
                      },
                    }}
                  >
                    <Avatar
                      sx={{
                        mr: 2,
                        background: `linear-gradient(135deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.dark})`,
                        fontWeight: 600,
                      }}
                    >
                      {index + 1}
                    </Avatar>
                    <ListItemText
                      primary={
                        <Typography variant="body1" sx={{ fontWeight: 600 }}>
                          {brand.brand_name}
                        </Typography>
                      }
                      secondary={
                        <Typography variant="body2" color="text.secondary">
                          {brand.mention_count} {brand.mention_count === 1 ? 'mention' : 'mentions'}
                        </Typography>
                      }
                    />
                    <Chip
                      label={brand.mention_count}
                      color="secondary"
                      sx={{ fontWeight: 600, minWidth: 60 }}
                    />
                  </ListItem>
                </motion.div>
              ))}
            </List>
          )}

          {topBrands && topBrands.total > brandsPageSize && (
            <Box display="flex" justifyContent="center" mt={3}>
              <Pagination
                count={Math.ceil(topBrands.total / brandsPageSize)}
                page={brandsPage}
                onChange={(_, page) => setBrandsPage(page)}
                color="primary"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </CardContent>
      </MotionCard>
    </Box>
  );
};

export default Dashboard;
