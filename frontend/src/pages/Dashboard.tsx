import React, { useState } from 'react';
import {
  Container,
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
  AppBar,
  Toolbar,
  Collapse,
  IconButton,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon } from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { reportsApi } from '../api/reports';
import { brandsApi } from '../api/brands';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';

const Dashboard: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [expandedReports, setExpandedReports] = useState<Set<string>>(new Set());

  const { data: analytics, isLoading: analyticsLoading, error: analyticsError } = useQuery({
    queryKey: ['analytics', 'overview'],
    queryFn: () => analyticsApi.getOverview(),
  });

  const { data: reportsData, isLoading: reportsLoading } = useQuery({
    queryKey: ['reports', 'recent'],
    queryFn: () => reportsApi.getRecentReports(5),
  });

  const { data: topBrands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands', 'top'],
    queryFn: () => brandsApi.getTopBrands(5),
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
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

  if (analyticsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="100vh">
        <CircularProgress />
      </Box>
    );
  }

  if (analyticsError) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="error">
          Failed to load analytics data. Please try again later.
        </Alert>
      </Container>
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
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            ABMC Media Tracker
          </Typography>
          {user && (
            <>
              <Typography variant="body2" sx={{ mr: 2 }}>
                {user.email} ({user.role})
              </Typography>
              {user.tenant_name && (
                <Typography variant="body2" sx={{ mr: 2 }}>
                  | {user.tenant_name}
                </Typography>
              )}
              <Button color="inherit" onClick={handleLogout}>
                Logout
              </Button>
            </>
          )}
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
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
          <Typography variant="h5" gutterBottom>
            Recent Reports
          </Typography>
          {reportsLoading ? (
            <CircularProgress />
          ) : (
<List>
              {reportsData?.map((report) => {
                const isExpanded = expandedReports.has(report.id);
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
                      <Box flex={1}>
                        <Box display="flex" alignItems="center" gap={1} mb={1}>
                          <Typography variant="subtitle1" fontWeight="bold">
                            {report.title}
                          </Typography>
                          <Chip
                            label={report.sentiment}
                            color={getSentimentColor(report.sentiment)}
                            size="small"
                          />
                        </Box>

                        <Typography variant="body2" color="text.secondary" mb={1}>
                          {report.source} • {new Date(report.timestamp).toLocaleDateString()}
                        </Typography>

                        {report.brands && report.brands.length > 0 && (
                          <Box mb={1}>
                            {report.brands.map((brand, idx) => (
                              <Chip
                                key={idx}
                                label={brand}
                                size="small"
                                variant="outlined"
                                sx={{ mr: 0.5, mb: 0.5 }}
                              />
                            ))}
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
                  </ListItem>
                );
              })}
            </List>
          )}
        </Paper>

        {/* Top Brands */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Top Brands
          </Typography>
          {brandsLoading ? (
            <CircularProgress />
          ) : (
            <List>
              {topBrands?.map((brand) => (
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
        </Paper>
      </Container>
    </>
  );
};

export default Dashboard;
