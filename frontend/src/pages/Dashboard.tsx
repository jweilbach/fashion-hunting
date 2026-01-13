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
  Divider,
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
  Instagram as InstagramIcon,
  Article as ArticleIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { reportsApi } from '../api/reports';
import { brandsApi } from '../api/brands';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import { ReportColumn } from '../components/ReportColumn';
import QuickSearchWidget from '../components/QuickSearchWidget';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Dashboard: React.FC = () => {
  const theme = useTheme();
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());
  const [brandsPageSize, setBrandsPageSize] = useState<number>(10);
  const [brandsPage, setBrandsPage] = useState<number>(1);
  const [socialPage, setSocialPage] = useState<number>(1);
  const [digitalPage, setDigitalPage] = useState<number>(1);
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

  // Fetch social and digital reports separately with pagination
  const { data: socialReportsData, isLoading: socialReportsLoading } = useQuery({
    queryKey: ['reports', 'recent', 'social', socialPage],
    queryFn: () => reportsApi.getRecentReports(10, (socialPage - 1) * 10, 'social'),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  const { data: digitalReportsData, isLoading: digitalReportsLoading } = useQuery({
    queryKey: ['reports', 'recent', 'digital', digitalPage],
    queryFn: () => reportsApi.getRecentReports(10, (digitalPage - 1) * 10, 'digital'),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  const reportsLoading = socialReportsLoading || digitalReportsLoading;

  const { data: topBrands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands', 'top', brandsPageSize, brandsPage],
    queryFn: () => brandsApi.getTopBrands(brandsPageSize, (brandsPage - 1) * brandsPageSize),
    refetchInterval: hasRunningJobs ? 10000 : false, // Refresh every 10s when jobs running
  });

  // Generate mock chart data from recent reports
  const getChartData = () => {
    const allReports = [...(socialReportsData?.items || []), ...(digitalReportsData?.items || [])];
    if (allReports.length === 0) return [];

    // Group reports by date
    const dateCounts: Record<string, number> = {};
    allReports.forEach((report) => {
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
    const allReports = [...(socialReportsData?.items || []), ...(digitalReportsData?.items || [])];
    if (selectedReports.size === allReports.length && allReports.length > 0) {
      setSelectedReports(new Set());
    } else {
      setSelectedReports(new Set(allReports.map(r => r.id)));
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
    <Box sx={{ width: '100%' }}>
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

      {/* Quick Search Widget */}
      <MotionBox
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.35 }}
      >
        <QuickSearchWidget onSearchComplete={() => {
          // Invalidate reports queries to refresh the list
          queryClient.invalidateQueries({ queryKey: ['reports'] });
          queryClient.invalidateQueries({ queryKey: ['analytics'] });
        }} />
      </MotionBox>

      {/* Recent Reports */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        sx={{ mb: 4 }}
      >
        <CardContent sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
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

          {reportsLoading ? (
            <Box display="flex" justifyContent="center" py={4}>
              <CircularProgress />
            </Box>
          ) : (
            <Box display="flex" gap={3} sx={{ height: '70vh', minHeight: '500px' }}>
              {/* Social Media Column */}
              <ReportColumn
                title="Social Media"
                icon={<InstagramIcon />}
                reports={socialReportsData?.items || []}
                totalCount={socialReportsData?.total || 0}
                color={theme.palette.info.main}
                expandedReports={expandedReports}
                selectedReports={selectedReports}
                onToggleExpansion={toggleReportExpansion}
                onToggleSelection={toggleReportSelection}
                onPageChange={setSocialPage}
                currentPage={socialPage}
                getSentimentColor={getSentimentColor}
                knownBrandNames={knownBrandNames}
                sortBrands={sortBrands}
              />

              {/* Digital Media Column */}
              <ReportColumn
                title="Digital Media"
                icon={<ArticleIcon />}
                reports={digitalReportsData?.items || []}
                totalCount={digitalReportsData?.total || 0}
                color={theme.palette.primary.main}
                expandedReports={expandedReports}
                selectedReports={selectedReports}
                onToggleExpansion={toggleReportExpansion}
                onToggleSelection={toggleReportSelection}
                onPageChange={setDigitalPage}
                currentPage={digitalPage}
                getSentimentColor={getSentimentColor}
                knownBrandNames={knownBrandNames}
                sortBrands={sortBrands}
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
