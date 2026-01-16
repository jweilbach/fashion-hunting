import React, { useState } from 'react';
import {
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Chip,
  CircularProgress,
  Alert,
  Switch,
  FormControlLabel,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  OutlinedInput,
  Divider,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  alpha,
  useTheme,
  Avatar,
  Stack,
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  PlayArrow as RunIcon,
  CheckCircle as SuccessIcon,
  Cancel as DisabledIcon,
  Schedule as ScheduleIcon,
  ExpandMore as ExpandMoreIcon,
  EventRepeat as DailyIcon,
  CalendarToday as WeeklyIcon,
  TouchApp as ManualIcon,
  Code as CustomIcon,
  Error as ErrorIcon,
  HourglassEmpty as RunningIcon,
  AccessTime as TimeIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, type ScheduledJob, type ScheduledJobCreate } from '../api/jobs';
import { brandsApi } from '../api/brands';
import { feedsApi, type Feed } from '../api/feeds';
import type { Brand } from '../types';
import { motion } from 'framer-motion';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Jobs: React.FC = () => {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null);
  const [runningJobIds, setRunningJobIds] = useState<Set<string>>(new Set());
  const [formData, setFormData] = useState({
    name: '',
    brand_ids: [] as string[],
    feed_ids: [] as string[],
    schedule_type: 'manual',
    custom_cron: '',
    enabled: true,
    generate_summary: false, // Brand 360 - generate AI summary after execution
    // Advanced settings
    enable_html_brand_extraction: false,
    max_html_size_bytes: 500000,
    unlimited_html_size: false,
    max_items_per_run: 10,
    ignore_brand_exact: [] as string[],
    ignore_brand_patterns: [] as string[],
  });

  const queryClient = useQueryClient();

  const { data: jobs, isLoading: jobsLoading, error: jobsError } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.getJobs(),
    refetchInterval: (query) => {
      // Auto-refresh every 5 seconds if any job is running
      const hasRunningJobs = query.state.data?.some((job: ScheduledJob) => job.last_status === 'running');
      return hasRunningJobs ? 5000 : false;
    },
  });

  const { data: brands, isLoading: brandsLoading } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.getBrands(),
  });

  const { data: feeds, isLoading: feedsLoading } = useQuery({
    queryKey: ['feeds'],
    queryFn: () => feedsApi.getFeeds(),
  });

  const createMutation = useMutation({
    mutationFn: (data: ScheduledJobCreate) => jobsApi.createJob(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      handleClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      jobsApi.updateJob(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      handleClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => jobsApi.deleteJob(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const runMutation = useMutation({
    mutationFn: (id: string) => jobsApi.runJobNow(id),
    onSuccess: (_data, jobId) => {
      // Invalidate queries to refresh the UI
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
      queryClient.invalidateQueries({ queryKey: ['executions'] });

      // Keep job in running state for 5 seconds, then clear
      // This gives the backend time to update the job status
      setTimeout(() => {
        setRunningJobIds(prev => {
          const next = new Set(prev);
          next.delete(jobId);
          return next;
        });
      }, 5000);
    },
    onError: (_error, jobId) => {
      // Remove from running jobs on error
      setRunningJobIds(prev => {
        const next = new Set(prev);
        next.delete(jobId);
        return next;
      });
    },
  });

  const handleOpen = (job?: ScheduledJob) => {
    if (job) {
      setEditingJob(job);
      const scheduleType = job.schedule_cron === '@manual' ? 'manual' :
        job.schedule_cron === '0 9 * * *' ? 'daily' :
        job.schedule_cron === '0 9 * * 1' ? 'weekly' : 'custom';

      setFormData({
        name: job.config?.name || '',
        brand_ids: job.config?.brand_ids || [],
        feed_ids: job.config?.feed_ids || [],
        schedule_type: scheduleType,
        custom_cron: scheduleType === 'custom' ? job.schedule_cron : '',
        enabled: job.enabled,
        generate_summary: job.generate_summary || false,
        // Advanced settings
        enable_html_brand_extraction: job.config?.enable_html_brand_extraction || false,
        max_html_size_bytes: job.config?.max_html_size_bytes ?? 500000,
        unlimited_html_size: job.config?.max_html_size_bytes === null,
        max_items_per_run: job.config?.max_items_per_run || 10,
        ignore_brand_exact: job.config?.ignore_brand_exact || [],
        ignore_brand_patterns: job.config?.ignore_brand_patterns || [],
      });
    } else {
      setEditingJob(null);
      setFormData({
        name: '',
        brand_ids: [],
        feed_ids: [],
        schedule_type: 'manual',
        custom_cron: '',
        enabled: true,
        generate_summary: false,
        // Advanced settings defaults
        enable_html_brand_extraction: false,
        max_html_size_bytes: 500000,
        unlimited_html_size: false,
        max_items_per_run: 10,
        ignore_brand_exact: [],
        ignore_brand_patterns: [],
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingJob(null);
  };

  const handleBrandChange = async (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    const newBrandIds = typeof value === 'string' ? value.split(',') : value;

    // Find newly added brands (brands that weren't selected before)
    const addedBrandIds = newBrandIds.filter(id => !formData.brand_ids.includes(id));

    // Fetch feeds for newly added brands and add them to feed_ids
    let newFeedIds = [...formData.feed_ids];
    for (const brandId of addedBrandIds) {
      try {
        const brandFeeds = await brandsApi.getBrandFeeds(brandId);
        const feedIds = brandFeeds.map(f => f.id);
        // Add feed IDs that aren't already selected
        feedIds.forEach(id => {
          if (!newFeedIds.includes(id)) {
            newFeedIds.push(id);
          }
        });
      } catch (error) {
        console.error(`Failed to fetch feeds for brand ${brandId}:`, error);
      }
    }

    setFormData({
      ...formData,
      brand_ids: newBrandIds,
      feed_ids: newFeedIds,
    });
  };

  const handleFeedChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setFormData({
      ...formData,
      feed_ids: typeof value === 'string' ? value.split(',') : value,
    });
  };

  const getScheduleCron = (): string => {
    switch (formData.schedule_type) {
      case 'manual':
        return '@manual';
      case 'daily':
        return '0 9 * * *';
      case 'weekly':
        return '0 9 * * 1';
      case 'custom':
        return formData.custom_cron;
      default:
        return '@manual';
    }
  };

  const handleSubmit = () => {
    const submitData = {
      job_type: 'monitor_feeds',
      schedule_cron: getScheduleCron(),
      enabled: formData.enabled,
      generate_summary: formData.generate_summary,
      config: {
        name: formData.name,
        brand_ids: formData.brand_ids,
        feed_ids: formData.feed_ids,
        // Advanced settings
        enable_html_brand_extraction: formData.enable_html_brand_extraction,
        max_html_size_bytes: formData.unlimited_html_size ? null : formData.max_html_size_bytes,
        max_items_per_run: formData.max_items_per_run,
        ignore_brand_exact: formData.ignore_brand_exact,
        ignore_brand_patterns: formData.ignore_brand_patterns,
      },
    };

    if (editingJob) {
      const updateData = {
        schedule_cron: getScheduleCron(),
        enabled: formData.enabled,
        generate_summary: formData.generate_summary,
        config: {
          name: formData.name,
          brand_ids: formData.brand_ids,
          feed_ids: formData.feed_ids,
          // Advanced settings
          enable_html_brand_extraction: formData.enable_html_brand_extraction,
          max_html_size_bytes: formData.unlimited_html_size ? null : formData.max_html_size_bytes,
          max_items_per_run: formData.max_items_per_run,
          ignore_brand_exact: formData.ignore_brand_exact,
          ignore_brand_patterns: formData.ignore_brand_patterns,
        },
      };
      updateMutation.mutate({ id: editingJob.id, data: updateData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this job?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleRunNow = (id: string) => {
    // Add to running jobs set immediately for UI feedback
    setRunningJobIds(prev => new Set(prev).add(id));
    runMutation.mutate(id);
  };

  const getScheduleLabel = (cron: string): string => {
    if (cron === '@manual') return 'Manual Only';
    if (cron === '0 9 * * *') return 'Daily at 9:00 AM';
    if (cron === '0 9 * * 1') return 'Weekly (Mondays at 9:00 AM)';
    return `Custom: ${cron}`;
  };

  const getScheduleIcon = (cron: string) => {
    if (cron === '@manual') return <ManualIcon />;
    if (cron === '0 9 * * *') return <DailyIcon />;
    if (cron === '0 9 * * 1') return <WeeklyIcon />;
    return <CustomIcon />;
  };

  const getScheduleColor = (cron: string) => {
    if (cron === '@manual') return theme.palette.text.secondary;
    if (cron === '0 9 * * *') return theme.palette.success.main;
    if (cron === '0 9 * * 1') return theme.palette.info.main;
    return theme.palette.warning.main;
  };

  const getStatusIcon = (job: ScheduledJob) => {
    if (!job.enabled) return <DisabledIcon />;
    if (!job.last_status) return <ScheduleIcon />;

    switch (job.last_status) {
      case 'success':
        return <SuccessIcon />;
      case 'failed':
        return <ErrorIcon />;
      case 'running':
        return <RunningIcon />;
      default:
        return <ScheduleIcon />;
    }
  };

  const getStatusColor = (job: ScheduledJob) => {
    if (!job.enabled) return 'default';
    if (!job.last_status) return 'info';

    switch (job.last_status) {
      case 'success':
        return 'success';
      case 'failed':
        return 'error';
      case 'running':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getStatusLabel = (job: ScheduledJob) => {
    if (!job.enabled) return 'Disabled';
    if (!job.last_status) return 'Never Run';

    switch (job.last_status) {
      case 'success':
        return 'Success';
      case 'failed':
        return 'Failed';
      case 'running':
        return 'Running';
      default:
        return job.last_status;
    }
  };

  const getBrandName = (brandId: string): string => {
    const brand = brands?.find((b: Brand) => b.id === brandId);
    return brand?.brand_name || brandId;
  };

  const getFeedLabel = (feedId: string): string => {
    const feed = feeds?.find((f: Feed) => f.id === feedId);
    return feed?.label || feed?.feed_value || feedId;
  };

  const formatDateTime = (dateStr?: string): string => {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleString();
  };

  if (jobsLoading || brandsLoading || feedsLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (jobsError) {
    return <Alert severity="error">Failed to load jobs. Please try again later.</Alert>;
  }

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
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box>
          <Typography variant="h3" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
            Jobs
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Schedule and manage automated brand monitoring tasks
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
          size="large"
          sx={{
            px: 3,
            py: 1.5,
          }}
        >
          Add Job
        </Button>
      </MotionBox>

      {/* Jobs Grid */}
      {(!jobs || jobs.length === 0) ? (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <ScheduleIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No jobs yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first monitoring job to automate brand tracking
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
            Add Job
          </Button>
        </Card>
      ) : (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {jobs?.map((job: ScheduledJob, index: number) => {
            const scheduleColor = getScheduleColor(job.schedule_cron);
            return (
              <MotionCard
                key={job.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                sx={{
                  '&:hover': {
                    transform: 'translateX(4px)',
                    boxShadow: `0 8px 24px ${alpha(scheduleColor, 0.15)}`,
                  },
                  transition: 'all 0.3s ease',
                  borderLeft: `4px solid ${scheduleColor}`,
                }}
              >
                <CardContent sx={{ p: 3 }}>
                  <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                    <Box display="flex" gap={2} flex={1}>
                      <Avatar
                        sx={{
                          width: 56,
                          height: 56,
                          background: `linear-gradient(135deg, ${scheduleColor}, ${alpha(scheduleColor, 0.7)})`,
                        }}
                      >
                        {getScheduleIcon(job.schedule_cron)}
                      </Avatar>

                      <Box flex={1}>
                        <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                          <Typography variant="h6" sx={{ fontWeight: 600 }}>
                            {job.config?.name || 'Unnamed Job'}
                          </Typography>
                          <Chip
                            icon={getStatusIcon(job)}
                            label={getStatusLabel(job)}
                            color={getStatusColor(job)}
                            size="small"
                            sx={{
                              fontWeight: 500,
                              ...(job.last_status === 'running' && {
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
                          />
                          {job.last_status === 'running' && (
                            <CircularProgress size={16} thickness={4} />
                          )}
                          {job.generate_summary && (
                            <Chip
                              label="AI Summary"
                              size="small"
                              color="secondary"
                              variant="outlined"
                              sx={{ fontWeight: 500 }}
                            />
                          )}
                        </Box>

                        <Stack direction="row" spacing={3} mb={1.5} flexWrap="wrap">
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <ScheduleIcon sx={{ fontSize: 14 }} />
                              Schedule
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {getScheduleLabel(job.schedule_cron)}
                            </Typography>
                          </Box>

                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <TimeIcon sx={{ fontSize: 14 }} />
                              Last Run
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {formatDateTime(job.last_run)}
                            </Typography>
                          </Box>

                          <Box>
                            <Typography variant="caption" color="text.secondary">
                              Executions
                            </Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {job.run_count}
                            </Typography>
                          </Box>
                        </Stack>

                        {/* Brands */}
                        {job.config?.brand_ids && job.config.brand_ids.length > 0 && (
                          <Box mb={1}>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 500 }}>
                              Brands:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                              {job.config.brand_ids.map((brandId: string) => (
                                <Chip
                                  key={brandId}
                                  label={getBrandName(brandId)}
                                  size="small"
                                  variant="outlined"
                                  sx={{ mb: 0.5 }}
                                />
                              ))}
                            </Stack>
                          </Box>
                        )}

                        {/* Feeds */}
                        {job.config?.feed_ids && job.config.feed_ids.length > 0 && (
                          <Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 500 }}>
                              Feeds:
                            </Typography>
                            <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                              {job.config.feed_ids.map((feedId: string) => (
                                <Chip
                                  key={feedId}
                                  label={getFeedLabel(feedId)}
                                  size="small"
                                  variant="outlined"
                                  color="primary"
                                  sx={{ mb: 0.5 }}
                                />
                              ))}
                            </Stack>
                          </Box>
                        )}
                      </Box>
                    </Box>

                    <Stack direction="row" spacing={1}>
                      <IconButton
                        size="small"
                        onClick={() => handleRunNow(job.id)}
                        disabled={
                          runMutation.isPending ||
                          job.last_status === 'running' ||
                          runningJobIds.has(job.id)
                        }
                        sx={{
                          color: theme.palette.success.main,
                          '&:hover': {
                            backgroundColor: alpha(theme.palette.success.main, 0.1),
                          },
                          '&.Mui-disabled': {
                            color: theme.palette.action.disabled,
                          },
                        }}
                        title={
                          job.last_status === 'running' || runningJobIds.has(job.id)
                            ? 'Job is already running'
                            : 'Run Now'
                        }
                      >
                        <RunIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleOpen(job)}
                        sx={{
                          color: theme.palette.primary.main,
                          '&:hover': {
                            backgroundColor: alpha(theme.palette.primary.main, 0.1),
                          },
                        }}
                        title="Edit"
                      >
                        <EditIcon />
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(job.id)}
                        sx={{
                          color: theme.palette.error.main,
                          '&:hover': {
                            backgroundColor: alpha(theme.palette.error.main, 0.1),
                          },
                        }}
                        title="Delete"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Stack>
                  </Box>
                </CardContent>
              </MotionCard>
            );
          })}
        </Box>
      )}

      {/* Add/Edit Dialog */}
      <Dialog
        open={open}
        onClose={handleClose}
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
            {editingJob ? 'Edit Job' : 'Create Job'}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="Job Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            required
            helperText="A descriptive name for this job"
          />

          <FormControl fullWidth margin="normal" required>
            <InputLabel>Brands to Monitor</InputLabel>
            <Select
              multiple
              value={formData.brand_ids}
              onChange={handleBrandChange}
              input={<OutlinedInput label="Brands to Monitor" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={getBrandName(value)} size="small" />
                  ))}
                </Box>
              )}
            >
              {brands?.map((brand: Brand) => (
                <MenuItem key={brand.id} value={brand.id}>
                  {brand.brand_name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary" sx={{ mt: -1, ml: 1.5 }}>
            Selecting a brand will automatically add its configured feeds
          </Typography>

          <FormControl fullWidth margin="normal" required>
            <InputLabel>Feeds to Monitor</InputLabel>
            <Select
              multiple
              value={formData.feed_ids}
              onChange={handleFeedChange}
              input={<OutlinedInput label="Feeds to Monitor" />}
              renderValue={(selected) => (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                  {selected.map((value) => (
                    <Chip key={value} label={getFeedLabel(value)} size="small" color="primary" />
                  ))}
                </Box>
              )}
            >
              {feeds?.map((feed: Feed) => (
                <MenuItem key={feed.id} value={feed.id}>
                  {feed.label || feed.feed_value} ({feed.provider})
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl fullWidth margin="normal" required>
            <InputLabel>Schedule</InputLabel>
            <Select
              value={formData.schedule_type}
              onChange={(e) => setFormData({ ...formData, schedule_type: e.target.value })}
              label="Schedule"
            >
              <MenuItem value="manual">Manual Only</MenuItem>
              <MenuItem value="daily">Daily at 9:00 AM</MenuItem>
              <MenuItem value="weekly">Weekly (Mondays at 9:00 AM)</MenuItem>
              <MenuItem value="custom">Custom Cron Expression</MenuItem>
            </Select>
          </FormControl>

          {formData.schedule_type === 'custom' && (
            <TextField
              fullWidth
              label="Cron Expression"
              value={formData.custom_cron}
              onChange={(e) => setFormData({ ...formData, custom_cron: e.target.value })}
              margin="normal"
              required
              helperText="e.g., '0 9 * * *' for daily at 9:00 AM"
            />
          )}

          {/* Advanced Settings */}
          <Accordion sx={{ mt: 3 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle1" fontWeight="medium">
                Advanced Settings
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {/* Max Items Per Run */}
                <TextField
                  fullWidth
                  label="Max Items Per Run"
                  type="number"
                  value={formData.max_items_per_run}
                  onChange={(e) => setFormData({ ...formData, max_items_per_run: parseInt(e.target.value) || 10 })}
                  helperText="Maximum number of items to process per execution"
                  slotProps={{ htmlInput: { min: 1, max: 100 } }}
                />

                {/* HTML Brand Extraction */}
                <FormControlLabel
                  control={
                    <Switch
                      checked={formData.enable_html_brand_extraction}
                      onChange={(e) => setFormData({ ...formData, enable_html_brand_extraction: e.target.checked })}
                    />
                  }
                  label="Enable HTML Brand Extraction (Hybrid Processing)"
                />
                <Typography variant="caption" color="text.secondary" sx={{ mt: -1 }}>
                  Extract brands from raw HTML in addition to article text. More comprehensive but slower and uses more AI credits.
                </Typography>

                {/* HTML Size Limit */}
                {formData.enable_html_brand_extraction && (
                  <>
                    <FormControlLabel
                      control={
                        <Switch
                          checked={formData.unlimited_html_size}
                          onChange={(e) => setFormData({ ...formData, unlimited_html_size: e.target.checked })}
                        />
                      }
                      label="Unlimited HTML Size"
                    />

                    {!formData.unlimited_html_size && (
                      <TextField
                        fullWidth
                        label="Max HTML Size (bytes)"
                        type="number"
                        value={formData.max_html_size_bytes}
                        onChange={(e) => setFormData({ ...formData, max_html_size_bytes: parseInt(e.target.value) || 500000 })}
                        helperText="Maximum HTML size to process (default: 500000 = 500KB)"
                        slotProps={{ htmlInput: { min: 1000, step: 10000 } }}
                      />
                    )}
                  </>
                )}

                <Divider sx={{ my: 1 }} />

                {/* Ignore Brand Exact */}
                <TextField
                  fullWidth
                  label="Ignore Brands (Exact Match)"
                  value={formData.ignore_brand_exact.join(', ')}
                  onChange={(e) => setFormData({
                    ...formData,
                    ignore_brand_exact: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  })}
                  helperText="Comma-separated list of brand names to ignore (e.g., CNN, BBC)"
                  multiline
                  rows={2}
                />

                {/* Ignore Brand Patterns */}
                <TextField
                  fullWidth
                  label="Ignore Brands (Regex Patterns)"
                  value={formData.ignore_brand_patterns.join(', ')}
                  onChange={(e) => setFormData({
                    ...formData,
                    ignore_brand_patterns: e.target.value.split(',').map(s => s.trim()).filter(Boolean)
                  })}
                  helperText="Comma-separated regex patterns (e.g., .*News.*, .*Media.*)"
                  multiline
                  rows={2}
                />
              </Box>
            </AccordionDetails>
          </Accordion>

          <FormControlLabel
            control={
              <Switch
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              />
            }
            label="Enabled"
            sx={{ mt: 2 }}
          />

          <Divider sx={{ my: 2 }} />

          {/* Generate Summary Option (Brand 360) */}
          <FormControlLabel
            control={
              <Switch
                checked={formData.generate_summary}
                onChange={(e) => setFormData({ ...formData, generate_summary: e.target.checked })}
              />
            }
            label="Generate AI Summary Document"
          />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', ml: 6, mt: -1 }}>
            Automatically create a PDF summary with AI-generated insights after this job completes
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 3, pt: 2 }}>
          <Button onClick={handleClose} size="large">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            size="large"
            disabled={
              !formData.name ||
              formData.brand_ids.length === 0 ||
              formData.feed_ids.length === 0 ||
              (formData.schedule_type === 'custom' && !formData.custom_cron) ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {editingJob ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success/Error Alerts */}
      {createMutation.isSuccess && (
        <Alert
          severity="success"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => createMutation.reset()}
        >
          Job created successfully
        </Alert>
      )}

      {createMutation.isError && (
        <Alert
          severity="error"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => createMutation.reset()}
        >
          Failed to create job. Please try again.
        </Alert>
      )}

      {updateMutation.isSuccess && (
        <Alert
          severity="success"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => updateMutation.reset()}
        >
          Job settings updated successfully
        </Alert>
      )}

      {updateMutation.isError && (
        <Alert
          severity="error"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => updateMutation.reset()}
        >
          Failed to update job. Please try again.
        </Alert>
      )}

      {runMutation.isSuccess && (
        <Alert
          severity="success"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => runMutation.reset()}
        >
          Job queued for execution
        </Alert>
      )}

      {runMutation.isError && (
        <Alert
          severity="error"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => runMutation.reset()}
        >
          {runMutation.error?.message?.includes('already running') || runMutation.error?.message?.includes('409')
            ? 'Job is already running. Please wait for the current execution to complete.'
            : 'Failed to run job. Please try again.'}
        </Alert>
      )}

      {deleteMutation.isSuccess && (
        <Alert
          severity="success"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => deleteMutation.reset()}
        >
          Job deleted successfully
        </Alert>
      )}

      {deleteMutation.isError && (
        <Alert
          severity="error"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            boxShadow: 3,
            borderRadius: 2,
            zIndex: 1300,
          }}
          onClose={() => deleteMutation.reset()}
        >
          Failed to delete job. Please try again.
        </Alert>
      )}
    </Box>
  );
};

export default Jobs;
