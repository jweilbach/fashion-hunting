import React, { useState } from 'react';
import {
  Typography,
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  HourglassEmpty as RunningIcon,
  Info as InfoIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { jobsApi, type JobExecution, type ScheduledJob } from '../api/jobs';

const History: React.FC = () => {
  const [selectedExecution, setSelectedExecution] = useState<JobExecution | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);

  const { data: executions, isLoading, error } = useQuery({
    queryKey: ['executions'],
    queryFn: () => jobsApi.getAllExecutions(),
    refetchInterval: 30000, // Refresh every 30 seconds to catch running jobs
  });

  const { data: jobs } = useQuery({
    queryKey: ['jobs'],
    queryFn: () => jobsApi.getJobs(),
  });

  const getJobName = (jobId: string): string => {
    const job = jobs?.find((j: ScheduledJob) => j.id === jobId);
    return job?.config?.name || 'Unknown Job';
  };

  const getStatusChip = (status: string) => {
    switch (status) {
      case 'success':
        return <Chip icon={<SuccessIcon />} label="Success" color="success" size="small" />;
      case 'failed':
        return <Chip icon={<ErrorIcon />} label="Failed" color="error" size="small" />;
      case 'running':
        return <Chip icon={<RunningIcon />} label="Running" color="warning" size="small" />;
      case 'partial':
        return <Chip icon={<InfoIcon />} label="Partial" color="info" size="small" />;
      default:
        return <Chip label={status} color="default" size="small" />;
    }
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h3">Execution History</Typography>
      </Box>

      {(!executions || executions.length === 0) ? (
        <Paper sx={{ p: 3 }}>
          <Typography variant="body1" color="text.secondary">
            No job executions yet. Create and run a task to see results here.
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Job Name</TableCell>
                <TableCell>Started</TableCell>
                <TableCell>Completed</TableCell>
                <TableCell>Duration</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Processed</TableCell>
                <TableCell>Failed</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {executions?.map((execution: JobExecution) => (
                <TableRow key={execution.id}>
                  <TableCell>
                    <strong>{getJobName(execution.job_id)}</strong>
                  </TableCell>
                  <TableCell>{formatDateTime(execution.started_at)}</TableCell>
                  <TableCell>
                    {execution.completed_at ? formatDateTime(execution.completed_at) : '-'}
                  </TableCell>
                  <TableCell>{getDuration(execution)}</TableCell>
                  <TableCell>{getStatusChip(execution.status)}</TableCell>
                  <TableCell>
                    <Chip label={execution.items_processed} color="success" size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>
                    {execution.items_failed > 0 ? (
                      <Chip label={execution.items_failed} color="error" size="small" variant="outlined" />
                    ) : (
                      <Chip label="0" color="default" size="small" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell align="right">
                    <Button
                      size="small"
                      onClick={() => handleViewDetails(execution)}
                      variant="outlined"
                    >
                      Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Details Dialog */}
      <Dialog open={detailsOpen} onClose={handleCloseDetails} maxWidth="md" fullWidth>
        <DialogTitle>Execution Details</DialogTitle>
        <DialogContent>
          {selectedExecution && (
            <Box>
              <Typography variant="h6" gutterBottom>
                Job: {getJobName(selectedExecution.job_id)}
              </Typography>

              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Status</Typography>
                <Box sx={{ mt: 0.5 }}>{getStatusChip(selectedExecution.status)}</Box>
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Timeline</Typography>
                <Typography variant="body2">
                  Started: {formatDateTime(selectedExecution.started_at)}
                </Typography>
                {selectedExecution.completed_at && (
                  <Typography variant="body2">
                    Completed: {formatDateTime(selectedExecution.completed_at)}
                  </Typography>
                )}
                <Typography variant="body2">
                  Duration: {getDuration(selectedExecution)}
                </Typography>
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary">Results</Typography>
                <Typography variant="body2">
                  Items Processed: {selectedExecution.items_processed}
                </Typography>
                <Typography variant="body2">
                  Items Failed: {selectedExecution.items_failed}
                </Typography>
              </Box>

              {selectedExecution.error_message && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" color="error">Error Message</Typography>
                  <Paper sx={{ p: 2, mt: 1, bgcolor: 'error.light', color: 'error.contrastText' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap' }}>
                      {selectedExecution.error_message}
                    </Typography>
                  </Paper>
                </Box>
              )}

              {selectedExecution.execution_log && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" color="text.secondary">Execution Log</Typography>
                  <Paper sx={{ p: 2, mt: 1, bgcolor: 'grey.100', maxHeight: 300, overflow: 'auto' }}>
                    <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
                      {selectedExecution.execution_log}
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDetails}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default History;
