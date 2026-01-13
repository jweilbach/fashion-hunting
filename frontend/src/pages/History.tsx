import React, { useState, useMemo } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  alpha,
  useTheme,
  Avatar,
  Stack,
  Paper,
  Divider,
  LinearProgress,
  Collapse,
  IconButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
} from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  HourglassEmpty as RunningIcon,
  Info as InfoIcon,
  AccessTime as TimeIcon,
  History as HistoryIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  FilterList as FilterIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { jobsApi, type JobExecution, type ScheduledJob } from '../api/jobs';
import { motion } from 'framer-motion';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

interface GroupedExecutions {
  jobId: string;
  jobName: string;
  executions: JobExecution[];
  totalExecutions: number;
  latestExecution: JobExecution;
}

const History: React.FC = () => {
  const theme = useTheme();
  const [selectedExecution, setSelectedExecution] = useState<JobExecution | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [expandedJobs, setExpandedJobs] = useState<Set<string>>(new Set());

  // Filter state
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [dateFilter, setDateFilter] = useState<string>('all'); // all, today, week, month
  const [jobFilter, setJobFilter] = useState<string>('');

  const { data: executions, isLoading, error } = useQuery({
    queryKey: ['executions'],
    queryFn: () => jobsApi.getAllExecutions(),
    refetchInterval: (query) => {
      // Auto-refresh every 5 seconds if any execution is running, otherwise every 30 seconds
      const hasRunningExecutions = query.state.data?.some((exec: JobExecution) => exec.status === 'running');
      return hasRunningExecutions ? 5000 : 30000;
    },
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.getJobs(),
  });

  const getJobName = (jobId: string): string => {
    const job = jobs?.find((j: ScheduledJob) => j.id === jobId);
    return job?.config?.name || 'Unknown Job';
  };

  // Filter executions based on filters
  const filteredExecutions = useMemo(() => {
    if (!executions) return [];

    return executions.filter((execution: JobExecution) => {
      // Status filter
      if (statusFilter && execution.status !== statusFilter) {
        return false;
      }

      // Job filter
      if (jobFilter && execution.job_id !== jobFilter) {
        return false;
      }

      // Date filter
      if (dateFilter !== 'all') {
        const execDate = new Date(execution.started_at);
        const now = new Date();
        const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());

        if (dateFilter === 'today') {
          if (execDate < startOfToday) return false;
        } else if (dateFilter === 'week') {
          const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          if (execDate < weekAgo) return false;
        } else if (dateFilter === 'month') {
          const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          if (execDate < monthAgo) return false;
        }
      }

      return true;
    });
  }, [executions, statusFilter, jobFilter, dateFilter]);

  // Group executions by job
  const groupedExecutions = useMemo(() => {
    if (!filteredExecutions || !jobs) return [];

    const grouped = new Map<string, GroupedExecutions>();

    filteredExecutions.forEach((execution: JobExecution) => {
      const jobId = execution.job_id;

      if (!grouped.has(jobId)) {
        grouped.set(jobId, {
          jobId,
          jobName: getJobName(jobId),
          executions: [],
          totalExecutions: 0,
          latestExecution: execution,
        });
      }

      const group = grouped.get(jobId)!;
      group.executions.push(execution);
      group.totalExecutions = group.executions.length;

      // Update latest execution if this one is more recent
      if (new Date(execution.started_at) > new Date(group.latestExecution.started_at)) {
        group.latestExecution = execution;
      }
    });

    // Convert to array and sort by latest execution date (most recent first)
    return Array.from(grouped.values()).sort((a, b) =>
      new Date(b.latestExecution.started_at).getTime() - new Date(a.latestExecution.started_at).getTime()
    );
  }, [filteredExecutions, jobs]);

  const toggleJobExpansion = (jobId: string) => {
    setExpandedJobs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(jobId)) {
        newSet.delete(jobId);
      } else {
        newSet.add(jobId);
      }
      return newSet;
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return theme.palette.success.main;
      case 'failed':
        return theme.palette.error.main;
      case 'running':
        return theme.palette.warning.main;
      case 'partial':
        return theme.palette.info.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <SuccessIcon />;
      case 'failed':
        return <ErrorIcon />;
      case 'running':
        return <RunningIcon />;
      case 'partial':
        return <InfoIcon />;
      default:
        return <HistoryIcon />;
    }
  };

  const getStatusChip = (status: string) => {
    const statusMap: Record<string, { label: string; color: 'success' | 'error' | 'warning' | 'info' | 'default' }> = {
      success: { label: 'Success', color: 'success' },
      failed: { label: 'Failed', color: 'error' },
      running: { label: 'Running', color: 'warning' },
      partial: { label: 'Partial', color: 'info' },
    };
    const config = statusMap[status] || { label: status, color: 'default' as const };
    return <Chip icon={getStatusIcon(status)} label={config.label} color={config.color} size="small" sx={{ fontWeight: 500 }} />;
  };

  const formatDateTime = (dateStr: string): string => {
    return new Date(dateStr).toLocaleString();
  };

  const getDuration = (execution: JobExecution): string => {
    if (!execution.completed_at) {
      return 'In Progress...';
    }
    const start = new Date(execution.started_at);
    const end = new Date(execution.completed_at);
    const durationMs = end.getTime() - start.getTime();
    const seconds = Math.floor(durationMs / 1000);

    if (seconds < 60) {
      return `${seconds}s`;
    } else if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes}m ${remainingSeconds}s`;
    } else {
      const hours = Math.floor(seconds / 3600);
      const remainingMinutes = Math.floor((seconds % 3600) / 60);
      return `${hours}h ${remainingMinutes}m`;
    }
  };

  const handleViewDetails = (execution: JobExecution) => {
    setSelectedExecution(execution);
    setDetailsOpen(true);
  };

  const handleCloseDetails = () => {
    setDetailsOpen(false);
    setSelectedExecution(null);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load execution history. Please try again later.</Alert>;
  }

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.info.light, 0.1)}, ${alpha(theme.palette.success.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Typography variant="h3" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
          History
        </Typography>
        <Typography variant="body1" color="text.secondary">
          View job execution history and results
        </Typography>
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
          {(statusFilter || dateFilter !== 'all' || jobFilter) && (
            <Chip
              label="Clear filters"
              size="small"
              onClick={() => {
                setStatusFilter('');
                setDateFilter('all');
                setJobFilter('');
              }}
              onDelete={() => {
                setStatusFilter('');
                setDateFilter('all');
                setJobFilter('');
              }}
              sx={{ ml: 'auto' }}
            />
          )}
        </Box>

        <Box display="flex" gap={2} flexWrap="wrap">
          {/* Status Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <MenuItem value="">All Statuses</MenuItem>
              <MenuItem value="success">Success</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
              <MenuItem value="running">Running</MenuItem>
              <MenuItem value="partial">Partial</MenuItem>
            </Select>
          </FormControl>

          {/* Date Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Date Range</InputLabel>
            <Select
              value={dateFilter}
              label="Date Range"
              onChange={(e) => setDateFilter(e.target.value)}
            >
              <MenuItem value="all">All Time</MenuItem>
              <MenuItem value="today">Today</MenuItem>
              <MenuItem value="week">Last 7 Days</MenuItem>
              <MenuItem value="month">Last 30 Days</MenuItem>
            </Select>
          </FormControl>

          {/* Job Filter */}
          <FormControl size="small" sx={{ minWidth: 200 }}>
            <InputLabel>Job</InputLabel>
            <Select
              value={jobFilter}
              label="Job"
              onChange={(e) => setJobFilter(e.target.value)}
            >
              <MenuItem value="">All Jobs</MenuItem>
              {jobs?.map((job: ScheduledJob) => (
                <MenuItem key={job.id} value={job.id}>
                  {job.config?.name || 'Unnamed Job'}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Filter Results Count */}
        {executions && executions.length > 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
            Showing {filteredExecutions.length} of {executions.length} executions
          </Typography>
        )}
      </Paper>

      {/* Grouped Executions */}
      {(!executions || executions.length === 0) ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <HistoryIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No executions yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Run a job to see execution results here
          </Typography>
        </Card>
      ) : filteredExecutions.length === 0 ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <FilterIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No matching executions
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Try adjusting your filters to see more results
          </Typography>
          <Button
            variant="outlined"
            sx={{ mt: 2 }}
            onClick={() => {
              setStatusFilter('');
              setDateFilter('all');
              setJobFilter('');
            }}
          >
            Clear Filters
          </Button>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {groupedExecutions.map((group: GroupedExecutions, index: number) => {
            const execution = group.latestExecution;
            const statusColor = getStatusColor(execution.status);
            const isExpanded = expandedJobs.has(group.jobId);
            const previousExecutions = group.executions
              .filter(e => e.id !== execution.id)
              .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());

            return (
              <MotionCard
                key={group.jobId}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                sx={{
                  '&:hover': {
                    transform: 'translateX(4px)',
                    boxShadow: `0 8px 24px ${alpha(statusColor, 0.15)}`,
                  },
                  transition: 'all 0.3s ease',
                  borderLeft: `4px solid ${statusColor}`,
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  {/* Latest Execution */}
                  <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                    <Box display="flex" gap={2} flex={1}>
                      <Avatar
                        sx={{
                          width: 56,
                          height: 56,
                          background: `linear-gradient(135deg, ${statusColor}, ${alpha(statusColor, 0.7)})`,
                        }}
                      >
                        {getStatusIcon(execution.status)}
                      </Avatar>

                      <Box flex={1}>
                        <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {group.jobName}
                          </Typography>
                          <Box
                            sx={{
                              ...(execution.status === 'running' && {
                                animation: 'pulse 2s ease-in-out infinite',
                                '@keyframes pulse': {
                                  '0%, 100%': {
                                    opacity: 1,
                                  },
                                  '50%': {
                                    opacity: 0.7,
                                  },
                                },
                              }),
                            }}
                          >
                            {getStatusChip(execution.status)}
                          </Box>
                          {execution.status === 'running' && (
                            <CircularProgress size={16} thickness={4} />
                          )}
                          <Chip
                            label={`${group.totalExecutions} total run${group.totalExecutions !== 1 ? 's' : ''}`}
                            size="small"
                            sx={{
                              backgroundColor: alpha(theme.palette.primary.main, 0.1),
                              color: theme.palette.primary.main,
                              fontWeight: 500,
                            }}
                          />
                        </Box>

                        {/* Progress Bar for Running Jobs */}
                        {execution.status === 'running' && execution.total_items > 0 && (
                          <Box sx={{ mb: 1.5 }}>
                            <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                              <Typography variant="caption" color="text.secondary">
                                Processing: {execution.current_item_title || 'Loading...'}
                              </Typography>
                              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                                {execution.current_item_index} / {execution.total_items}
                              </Typography>
                            </Box>
                            <LinearProgress
                              variant="determinate"
                              value={(execution.current_item_index / execution.total_items) * 100}
                              sx={{
                                height: 6,
                                borderRadius: 1,
                                backgroundColor: alpha(theme.palette.warning.main, 0.2),
                                '& .MuiLinearProgress-bar': {
                                  borderRadius: 1,
                                  backgroundColor: theme.palette.warning.main,
                                },
                              }}
                            />
                          </Box>
                        )}

                        <Stack direction="row" spacing={3} mb={1.5} flexWrap="wrap">
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <TimeIcon sx={{ fontSize: 14 }} />
                              Latest Run
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {formatDateTime(execution.started_at)}
                            </Typography>
                          </Box>

                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              Duration
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {getDuration(execution)}
                            </Typography>
                          </Box>
                        </Stack>

                        <Stack direction="row" spacing={2}>
                          <Chip
                            label={`${execution.items_processed} processed`}
                            size="small"
                            sx={{
                              backgroundColor: alpha(theme.palette.success.main, 0.1),
                              color: theme.palette.success.main,
                              fontWeight: 500,
                            }}
                          />
                          {execution.items_failed > 0 && (
                            <Chip
                              label={`${execution.items_failed} failed`}
                              size="small"
                              sx={{
                                backgroundColor: alpha(theme.palette.error.main, 0.1),
                                color: theme.palette.error.main,
                                fontWeight: 500,
                              }}
                            />
                          )}
                        </Stack>
                      </Box>
                    </Box>

                    <Stack direction="row" spacing={1}>
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => handleViewDetails(execution)}
                        sx={{ minWidth: 90 }}
                      >
                        Details
                      </Button>
                      {previousExecutions.length > 0 && (
                        <IconButton
                          onClick={() => toggleJobExpansion(group.jobId)}
                          size="small"
                          sx={{
                            border: `1px solid ${theme.palette.divider}`,
                            borderRadius: 1,
                          }}
                        >
                          {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      )}
                    </Stack>
                  </Box>

                  {/* Previous Executions */}
                  {previousExecutions.length > 0 && (
                    <Collapse in={isExpanded}>
                      <Box sx={{ mt: 3, pt: 3, borderTop: `1px solid ${theme.palette.divider}` }}>
                        <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 2, fontWeight: 600 }}>
                          Previous Runs ({previousExecutions.length})
                        </Typography>
                        <Stack spacing={2}>
                          {previousExecutions.map((prevExec: JobExecution) => {
                            const prevStatusColor = getStatusColor(prevExec.status);
                            return (
                              <Paper
                                key={prevExec.id}
                                sx={{
                                  p: 2,
                                  backgroundColor: alpha(theme.palette.background.default, 0.5),
                                  borderLeft: `3px solid ${prevStatusColor}`,
                                }}
                              >
                                <Box display="flex" alignItems="center" justifyContent="space-between">
                                  <Box flex={1}>
                                    <Box display="flex" alignItems="center" gap={1} mb={1}>
                                      {getStatusChip(prevExec.status)}
                                      <Typography variant="body2" color="text.secondary">
                                        {formatDateTime(prevExec.started_at)}
                                      </Typography>
                                    </Box>
                                    <Stack direction="row" spacing={2}>
                                      <Typography variant="caption" color="text.secondary">
                                        Duration: {getDuration(prevExec)}
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        Processed: {prevExec.items_processed}
                                      </Typography>
                                      {prevExec.items_failed > 0 && (
                                        <Typography variant="caption" color="error.main">
                                          Failed: {prevExec.items_failed}
                                        </Typography>
                                      )}
                                    </Stack>
                                  </Box>
                                  <Button
                                    variant="text"
                                    size="small"
                                    onClick={() => handleViewDetails(prevExec)}
                                  >
                                    View
                                  </Button>
                                </Box>
                              </Paper>
                            );
                          })}
                        </Stack>
                      </Box>
                    </Collapse>
                  )}
                </CardContent>
              </MotionCard>
            );
          })}
        </Box>
      )}

      {/* Details Dialog */}
      <Dialog
        open={detailsOpen}
        onClose={handleCloseDetails}
        maxWidth="md"
        fullWidth
        slotProps={{
          paper: {
            sx: {
              borderRadius: 3,
            },
          },
        }}
      >
        <DialogTitle sx={{ pb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 600 }}>
            Execution Details
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {selectedExecution && (
            <Box>
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  {getJobName(selectedExecution.job_id)}
                </Typography>
                {getStatusChip(selectedExecution.status)}
              </Box>

              <Divider sx={{ my: 2 }} />

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Timeline
                </Typography>
                <Stack spacing={1}>
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Started:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {formatDateTime(selectedExecution.started_at)}
                    </Typography>
                  </Box>
                  {selectedExecution.completed_at && (
                    <Box display="flex" justifyContent="space-between">
                      <Typography variant="body2">Completed:</Typography>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {formatDateTime(selectedExecution.completed_at)}
                      </Typography>
                    </Box>
                  )}
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="body2">Duration:</Typography>
                    <Typography variant="body2" sx={{ fontWeight: 500 }}>
                      {getDuration(selectedExecution)}
                    </Typography>
                  </Box>
                </Stack>
              </Box>

              <Divider sx={{ my: 2 }} />

              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Results
                </Typography>
                <Stack direction="row" spacing={2}>
                  <Chip
                    label={`${selectedExecution.items_processed} processed`}
                    color="success"
                    sx={{ fontWeight: 500 }}
                  />
                  <Chip
                    label={`${selectedExecution.items_failed} failed`}
                    color={selectedExecution.items_failed > 0 ? 'error' : 'default'}
                    sx={{ fontWeight: 500 }}
                  />
                </Stack>
              </Box>

              {selectedExecution.error_message && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box sx={{ mb: 3 }}>
                    <Typography variant="subtitle2" color="error" gutterBottom>
                      Error Message
                    </Typography>
                    <Paper
                      sx={{
                        p: 2,
                        backgroundColor: alpha(theme.palette.error.light, 0.1),
                        border: `1px solid ${alpha(theme.palette.error.main, 0.2)}`,
                        borderRadius: 2,
                      }}
                    >
                      <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', color: 'error.main' }}>
                        {selectedExecution.error_message}
                      </Typography>
                    </Paper>
                  </Box>
                </>
              )}

              {selectedExecution.execution_log && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Box>
                    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                      Execution Log
                    </Typography>
                    <Paper
                      sx={{
                        p: 2,
                        backgroundColor: alpha(theme.palette.text.primary, 0.03),
                        border: `1px solid ${theme.palette.divider}`,
                        borderRadius: 2,
                        maxHeight: 300,
                        overflow: 'auto',
                      }}
                    >
                      <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: '0.8rem' }}>
                        {selectedExecution.execution_log}
                      </Typography>
                    </Paper>
                  </Box>
                </>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 3, pt: 2 }}>
          <Button onClick={handleCloseDetails} size="large" variant="contained">
            Close
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default History;
