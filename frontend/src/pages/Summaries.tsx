import React, { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  alpha,
  useTheme,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Pagination,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
} from '@mui/material';
import {
  Summarize as SummariesIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { summariesApi } from '../api/summaries';
import SummaryList from '../components/SummaryList';
import { motion } from 'framer-motion';
import type { Summary } from '../types';

const MotionBox = motion.create(Box);

const Summaries: React.FC = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [summaryToDelete, setSummaryToDelete] = useState<Summary | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['summaries', page, pageSize, statusFilter],
    queryFn: () => summariesApi.getSummaries(page, pageSize, statusFilter || undefined),
  });

  const deleteMutation = useMutation({
    mutationFn: (summaryId: string) => summariesApi.deleteSummary(summaryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['summaries'] });
      setDeleteDialogOpen(false);
      setSummaryToDelete(null);
    },
  });

  const handleDownload = async (summaryId: string) => {
    try {
      const summary = data?.items.find(s => s.id === summaryId);
      const filename = summary ? `${summary.title.replace(/[^a-z0-9]/gi, '_')}.pdf` : undefined;
      await summariesApi.triggerSummaryDownload(summaryId, filename);
    } catch (err) {
      console.error('Failed to download summary:', err);
    }
  };

  const handleDeleteClick = (summaryId: string) => {
    const summary = data?.items.find(s => s.id === summaryId);
    if (summary) {
      setSummaryToDelete(summary);
      setDeleteDialogOpen(true);
    }
  };

  const handleConfirmDelete = () => {
    if (summaryToDelete) {
      deleteMutation.mutate(summaryToDelete.id);
    }
  };

  const handlePageChange = (_: React.ChangeEvent<unknown>, value: number) => {
    setPage(value);
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load summaries. Please try again later.</Alert>;
  }

  const summaries = data?.items || [];
  const totalPages = data?.pages || 1;

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.error.light, 0.1)}, ${alpha(theme.palette.primary.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={2}>
          <Box>
            <Typography variant="h3" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
              Summaries
            </Typography>
            <Typography variant="body1" color="text.secondary">
              AI-generated PDF summary documents from your media coverage
            </Typography>
          </Box>

          {/* Status Filter */}
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>Status</InputLabel>
            <Select
              value={statusFilter}
              label="Status"
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
            >
              <MenuItem value="">All</MenuItem>
              <MenuItem value="completed">Completed</MenuItem>
              <MenuItem value="generating">Generating</MenuItem>
              <MenuItem value="pending">Pending</MenuItem>
              <MenuItem value="failed">Failed</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </MotionBox>

      {/* Summary Count */}
      {data && (
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Showing {summaries.length} of {data.total} summaries
        </Typography>
      )}

      {/* Summaries List */}
      <Card>
        <CardContent>
          <SummaryList
            summaries={summaries}
            onDownload={handleDownload}
            onDelete={handleDeleteClick}
            showDelete
          />
        </CardContent>
      </Card>

      {/* Empty State */}
      {summaries.length === 0 && (
        <Card sx={{ p: 6, textAlign: 'center', mt: 2 }}>
          <SummariesIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No summaries yet
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Summaries are automatically generated when jobs with "Generate Summary" enabled complete.
          </Typography>
        </Card>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <Stack direction="row" justifyContent="center" sx={{ mt: 3 }}>
          <Pagination
            count={totalPages}
            page={page}
            onChange={handlePageChange}
            color="primary"
            showFirstButton
            showLastButton
          />
        </Stack>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Delete Summary
          </Typography>
        </DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this summary?
          </Typography>
          {summaryToDelete && (
            <Box sx={{ mt: 2, p: 2, bgcolor: alpha(theme.palette.error.main, 0.1), borderRadius: 1 }}>
              <Typography variant="subtitle2" fontWeight={600}>
                {summaryToDelete.title}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {summaryToDelete.report_count} reports
              </Typography>
            </Box>
          )}
          <Typography variant="body2" color="error" sx={{ mt: 2 }}>
            This action cannot be undone. The PDF file will also be permanently deleted.
          </Typography>
        </DialogContent>
        <DialogActions sx={{ p: 2 }}>
          <Button onClick={() => setDeleteDialogOpen(false)}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleConfirmDelete}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Summaries;
