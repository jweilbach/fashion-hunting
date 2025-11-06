import React, { useState } from 'react';
import {
  Typography,
  Box,
  Grid,
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
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon, Delete as DeleteIcon } from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { reportsApi } from '../api/reports';
import { brandsApi } from '../api/brands';

const Dashboard: React.FC = () => {
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());
  const [reportsPageSize, setReportsPageSize] = useState<number>(10);
  const [brandsPageSize, setBrandsPageSize] = useState<number>(10);
  const [reportsPage, setReportsPage] = useState<number>(1);
  const [brandsPage, setBrandsPage] = useState<number>(1);
  const [selectedReports, setSelectedReports] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: () => analyticsApi.getOverview(),
  });

  const { data: reportsData, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', 'recent', reportsPageSize, reportsPage],
    queryFn: () => reportsApi.getRecentReports(reportsPageSize, (reportsPage - 1) * reportsPageSize),
  });

  const { data: topBrands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands', 'top', brandsPageSize, brandsPage],
    queryFn: () => brandsApi.getTopBrands(brandsPageSize, (brandsPage - 1) * brandsPageSize),
  });

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

  // Create a set of known brand names for quick lookup
  const knownBrandNames = new Set(topBrands?.items?.map(brand => brand.brand_name) || []);

  // Helper function to sort brands: known brands first, then others
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

  return (
    <Box>
        <Typography variant="h3" gutterBottom>
          Dashboard
        </Typography>

        {/* Overview Stats */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Reports
                </Typography>
                <Typography variant="h4">
                  {analytics?.total_reports ?? 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Total Brands
                </Typography>
                <Typography variant="h4">
                  {analytics?.total_brands ?? 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>

          <Grid item xs={12} sm={6} md={4}>
            <Card>
              <CardContent>
                <Typography color="text.secondary" gutterBottom>
                  Active Feeds
                </Typography>
                <Typography variant="h4">
                  {analytics?.active_feeds ?? 0}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Recent Reports */}
        <Paper sx={{ p: 3, mb: 4 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography variant="h5">
                Recent Reports
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
            <Box display="flex" alignItems="center" mb={1} ml={1}>
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
            <CircularProgress />
          ) : (
            <List>
              {reportsData?.items?.map((report) => {
                const isExpanded = expandedReports.has(report.id);
                const isSelected = selectedReports.has(report.id);
                return (
                  <ListItem
                    key={report.id}
                    sx={{
                      borderBottom: '1px solid #eee',
                      '&:last-child': { borderBottom: 'none' },
                      display: 'block',
                      py: 2,
                    }}
                  >
                    <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                      <Box display="flex" alignItems="flex-start" gap={1} flex={1}>
                        <Checkbox
                          checked={isSelected}
                          onChange={() => toggleReportSelection(report.id)}
                          size="small"
                          sx={{ mt: 0.5 }}
                        />
                        <Box flex={1}>
                          <Box display="flex" alignItems="center" gap={1} mb={1}>
                            <Link
                              href={report.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              underline="hover"
                              color="inherit"
                              sx={{ fontWeight: 'bold', fontSize: '1.05rem' }}
                            >
                              {report.title}
                            </Link>
                            <Chip
                              label={report.sentiment}
                              color={getSentimentColor(report.sentiment)}
                              size="small"
                            />
                          </Box>

                          <Typography variant="body2" color="text.secondary" mb={1}>
                            {report.source} • Article Published: {new Date(report.timestamp).toLocaleDateString()} • Report Created: {new Date(report.created_at || report.timestamp).toLocaleDateString()}
                          </Typography>

                          {report.brands && report.brands.length > 0 && (
                            <Box mb={1}>
                              {sortBrands(report.brands).map((brand, idx) => {
                                const isKnown = knownBrandNames.has(brand);
                                return (
                                  <Chip
                                    key={idx}
                                    label={brand}
                                    size="small"
                                    variant="outlined"
                                    sx={{
                                      mr: 0.5,
                                      mb: 0.5,
                                      ...(isKnown && {
                                        backgroundColor: '#e8f5e9',
                                        borderColor: '#4caf50',
                                        color: '#2e7d32',
                                        fontWeight: 'bold',
                                      }),
                                    }}
                                  />
                                );
                              })}
                            </Box>
                          )}

                          {/* Summary Section */}
                          {report.summary && (
                            <Box mt={1}>
                              <Collapse in={isExpanded} collapsedSize={60}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    color: 'text.secondary',
                                    backgroundColor: '#f5f5f5',
                                    p: 1.5,
                                    borderRadius: 1,
                                  }}
                                >
                                  {report.summary}
                                </Typography>
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
                    </Box>
                  </ListItem>
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
        </Paper>

        {/* Top Brands */}
        <Paper sx={{ p: 3 }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Typography variant="h5">
              Top Brands
            </Typography>
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
            <CircularProgress />
          ) : (
            <List>
              {topBrands?.items?.map((brand) => (
                <ListItem
                  key={brand.id}
                  sx={{
                    borderBottom: '1px solid #eee',
                    '&:last-child': { borderBottom: 'none' },
                  }}
                >
                  <ListItemText
                    primary={brand.brand_name}
                    secondary={`${brand.mention_count} mentions`}
                  />
                </ListItem>
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
        </Paper>
    </Box>
  );
};

export default Dashboard;
