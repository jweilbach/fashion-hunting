import React, { useState } from 'react';
import {
  Typography,
  Box,
  Button,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
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
} from '@mui/material';
import type { SelectChangeEvent } from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  PlayArrow as RunIcon,
  CheckCircle as EnabledIcon,
  Cancel as DisabledIcon,
  Schedule as ScheduleIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi, type ScheduledJob, type ScheduledJobCreate } from '../api/jobs';
import { brandsApi } from '../api/brands';
import { feedsApi, type Feed } from '../api/feeds';
import type { Brand } from '../types';

const Tasks: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [editingJob, setEditingJob] = useState<ScheduledJob | null>(null);
  const [formData, setFormData] = useState({
    name: '',
    brand_ids: [] as string[],
    feed_ids: [] as string[],
    schedule_type: 'manual',
    custom_cron: '',
    enabled: true,
  });

  const queryClient = useQueryClient();

  const { data: jobs, isLoading: jobsLoading, error: jobsError } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.getJobs(),
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
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
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingJob(null);
  };

  const handleBrandChange = (event: SelectChangeEvent<string[]>) => {
    const value = event.target.value;
    setFormData({
      ...formData,
      brand_ids: typeof value === 'string' ? value.split(',') : value,
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
      config: {
        name: formData.name,
        brand_ids: formData.brand_ids,
        feed_ids: formData.feed_ids,
      },
    };

    if (editingJob) {
      const updateData = {
        schedule_cron: getScheduleCron(),
        enabled: formData.enabled,
        config: {
          name: formData.name,
          brand_ids: formData.brand_ids,
          feed_ids: formData.feed_ids,
        },
      };
      updateMutation.mutate({ id: editingJob.id, data: updateData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this task?')) {
      deleteMutation.mutate(id);
    }
  };

  const handleRunNow = (id: string) => {
    runMutation.mutate(id);
  };

  const getScheduleLabel = (cron: string): string => {
    if (cron === '@manual') return 'Manual Only';
    if (cron === '0 9 * * *') return 'Daily at 9:00 AM';
    if (cron === '0 9 * * 1') return 'Weekly (Mondays at 9:00 AM)';
    return `Custom: ${cron}`;
  };

  const getStatusChip = (job: ScheduledJob) => {
    if (!job.enabled) {
      return <Chip icon={<DisabledIcon />} label="Disabled" color="default" size="small" />;
    }

    if (!job.last_status) {
      return <Chip icon={<ScheduleIcon />} label="Never Run" color="info" size="small" />;
    }

    switch (job.last_status) {
      case 'success':
        return <Chip icon={<EnabledIcon />} label="Success" color="success" size="small" />;
      case 'failed':
        return <Chip label="Failed" color="error" size="small" />;
      case 'running':
        return <Chip label="Running" color="warning" size="small" />;
      default:
        return <Chip label={job.last_status} color="default" size="small" />;
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
    if (!dateStr) return '-';
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
    return <Alert severity="error">Failed to load tasks. Please try again later.</Alert>;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h3">Tasks</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
        >
          Add Task
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Task Name</TableCell>
              <TableCell>Brands</TableCell>
              <TableCell>Feeds</TableCell>
              <TableCell>Schedule</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Last Run</TableCell>
              <TableCell>Run Count</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jobs?.map((job: ScheduledJob) => (
              <TableRow key={job.id}>
                <TableCell>
                  <strong>{job.config?.name || 'Unnamed Task'}</strong>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {job.config?.brand_ids?.map((brandId: string) => (
                      <Chip
                        key={brandId}
                        label={getBrandName(brandId)}
                        size="small"
                        variant="outlined"
                      />
                    )) || '-'}
                  </Box>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                    {job.config?.feed_ids?.map((feedId: string) => (
                      <Chip
                        key={feedId}
                        label={getFeedLabel(feedId)}
                        size="small"
                        variant="outlined"
                        color="primary"
                      />
                    )) || '-'}
                  </Box>
                </TableCell>
                <TableCell>{getScheduleLabel(job.schedule_cron)}</TableCell>
                <TableCell>{getStatusChip(job)}</TableCell>
                <TableCell>{formatDateTime(job.last_run)}</TableCell>
                <TableCell>{job.run_count}</TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => handleRunNow(job.id)}
                    color="success"
                    disabled={runMutation.isPending}
                    title="Run Now"
                  >
                    <RunIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleOpen(job)}
                    color="primary"
                    title="Edit"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(job.id)}
                    color="error"
                    title="Delete"
                  >
                    <DeleteIcon />
                  </IconButton>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Add/Edit Dialog */}
      <Dialog open={open} onClose={handleClose} maxWidth="md" fullWidth>
        <DialogTitle>{editingJob ? 'Edit Task' : 'Create Task'}</DialogTitle>
        <DialogContent>
          <TextField
            fullWidth
            label="Task Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            required
            helperText="A descriptive name for this task"
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
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
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

      {runMutation.isSuccess && (
        <Alert severity="success" sx={{ mt: 2 }} onClose={() => runMutation.reset()}>
          Task queued for execution
        </Alert>
      )}

      {runMutation.isError && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={() => runMutation.reset()}>
          Failed to run task. Please try again.
        </Alert>
      )}
    </Box>
  );
};

export default Tasks;
