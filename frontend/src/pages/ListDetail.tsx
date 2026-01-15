import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Typography,
  Box,
  Button,
  Card,
  CardContent,
  IconButton,
  Chip,
  CircularProgress,
  Alert,
  alpha,
  useTheme,
  Avatar,
  Stack,
  Checkbox,
  Tooltip,
  Menu,
  MenuItem,
} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Delete as DeleteIcon,
  Download as DownloadIcon,
  OpenInNew as OpenInNewIcon,
  List as ListIcon,
  SentimentSatisfied as PositiveIcon,
  SentimentNeutral as NeutralIcon,
  SentimentDissatisfied as NegativeIcon,
  CalendarToday as DateIcon,
  TrendingUp as ReachIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listsApi } from '../api/lists';
import { motion } from 'framer-motion';
import type { Report } from '../types';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const ListDetail: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const { listId } = useParams<{ listId: string }>();
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [exportMenuAnchor, setExportMenuAnchor] = useState<HTMLElement | null>(null);

  const queryClient = useQueryClient();

  const { data: list, isLoading, error } = useQuery({
    queryKey: ['list', listId],
    queryFn: () => listsApi.getList(listId!),
    enabled: !!listId,
  });

  const removeItemsMutation = useMutation({
    mutationFn: (itemIds: string[]) => listsApi.removeItems(listId!, itemIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['list', listId] });
      queryClient.invalidateQueries({ queryKey: ['lists'] });
      setSelectedItems(new Set());
    },
  });

  const toggleSelected = (itemId: string) => {
    setSelectedItems((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(itemId)) {
        newSet.delete(itemId);
      } else {
        newSet.add(itemId);
      }
      return newSet;
    });
  };

  const selectAll = () => {
    if (list?.reports) {
      setSelectedItems(new Set(list.reports.map((r) => r.id)));
    }
  };

  const deselectAll = () => {
    setSelectedItems(new Set());
  };

  const handleRemoveSelected = () => {
    if (selectedItems.size === 0) return;
    if (window.confirm(`Remove ${selectedItems.size} items from this list?`)) {
      removeItemsMutation.mutate(Array.from(selectedItems));
    }
  };

  const handleExport = async (format: 'csv' | 'excel') => {
    if (!listId) return;
    try {
      await listsApi.exportList(listId, format);
    } catch (err) {
      console.error('Export failed:', err);
    }
    setExportMenuAnchor(null);
  };

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

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatReach = (reach: number): string => {
    if (reach >= 1000000) return `${(reach / 1000000).toFixed(1)}M`;
    if (reach >= 1000) return `${(reach / 1000).toFixed(1)}K`;
    return reach.toString();
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !list) {
    return <Alert severity="error">Failed to load list. Please try again later.</Alert>;
  }

  const reports = list.reports || [];
  const allSelected = reports.length > 0 && selectedItems.size === reports.length;

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.info.light, 0.1)}, ${alpha(theme.palette.primary.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Box display="flex" alignItems="center" gap={2} mb={2}>
          <IconButton onClick={() => navigate('/lists')} sx={{ mr: 1 }}>
            <BackIcon />
          </IconButton>
          <Avatar
            sx={{
              width: 56,
              height: 56,
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.info.main})`,
            }}
          >
            <ListIcon sx={{ fontSize: 28 }} />
          </Avatar>
          <Box flex={1}>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>
              {list.name}
            </Typography>
            {list.description && (
              <Typography variant="body1" color="text.secondary">
                {list.description}
              </Typography>
            )}
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              startIcon={<DownloadIcon />}
              onClick={(e) => setExportMenuAnchor(e.currentTarget)}
            >
              Export
            </Button>
            <Menu
              anchorEl={exportMenuAnchor}
              open={Boolean(exportMenuAnchor)}
              onClose={() => setExportMenuAnchor(null)}
            >
              <MenuItem onClick={() => handleExport('csv')}>Export as CSV</MenuItem>
              <MenuItem onClick={() => handleExport('excel')}>Export as Excel</MenuItem>
            </Menu>
          </Stack>
        </Box>
        <Stack direction="row" spacing={2}>
          <Chip label={`${reports.length} reports`} variant="outlined" />
          <Chip label={list.list_type} variant="outlined" sx={{ textTransform: 'capitalize' }} />
          <Typography variant="body2" color="text.secondary">
            Updated: {formatDate(list.updated_at)}
          </Typography>
        </Stack>
      </MotionBox>

      {/* Selection Actions */}
      {reports.length > 0 && (
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <Button size="small" onClick={allSelected ? deselectAll : selectAll}>
              {allSelected ? 'Deselect All' : 'Select All'}
            </Button>
            {selectedItems.size > 0 && (
              <Typography variant="body2" color="text.secondary">
                {selectedItems.size} selected
              </Typography>
            )}
          </Box>
          {selectedItems.size > 0 && (
            <Button
              size="small"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={handleRemoveSelected}
              disabled={removeItemsMutation.isPending}
            >
              Remove Selected
            </Button>
          )}
        </Box>
      )}

      {/* Reports List */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {reports.map((report: Report, index: number) => {
          const isSelected = selectedItems.has(report.id);
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
                }),
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="flex-start" gap={2}>
                  <Checkbox
                    checked={isSelected}
                    onChange={() => toggleSelected(report.id)}
                    sx={{ mt: -0.5 }}
                  />

                  <Avatar
                    sx={{
                      width: 48,
                      height: 48,
                      background: `linear-gradient(135deg, ${sentimentColor}, ${alpha(sentimentColor, 0.7)})`,
                    }}
                  >
                    {getSentimentIcon(report.sentiment)}
                  </Avatar>

                  <Box flex={1} minWidth={0}>
                    <Typography
                      variant="h6"
                      sx={{
                        fontWeight: 600,
                        mb: 1,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {report.title}
                    </Typography>

                    <Stack direction="row" spacing={2} mb={1.5} flexWrap="wrap" useFlexGap>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        <DateIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(report.timestamp)}
                        </Typography>
                      </Box>
                      <Box display="flex" alignItems="center" gap={0.5}>
                        <ReachIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          {formatReach(report.est_reach)} reach
                        </Typography>
                      </Box>
                      <Typography variant="caption" color="text.secondary">
                        {report.source}
                      </Typography>
                    </Stack>

                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{
                        mb: 2,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                      }}
                    >
                      {report.summary}
                    </Typography>

                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip
                        icon={getSentimentIcon(report.sentiment)}
                        label={report.sentiment}
                        size="small"
                        sx={{
                          backgroundColor: alpha(sentimentColor, 0.1),
                          color: sentimentColor,
                          fontWeight: 500,
                          textTransform: 'capitalize',
                        }}
                      />
                      {report.brands.slice(0, 2).map((brand) => (
                        <Chip
                          key={brand}
                          label={brand}
                          size="small"
                          variant="outlined"
                          sx={{ fontWeight: 500 }}
                        />
                      ))}
                      {report.brands.length > 2 && (
                        <Chip
                          label={`+${report.brands.length - 2}`}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Stack>
                  </Box>

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
              </CardContent>
            </MotionCard>
          );
        })}
      </Box>

      {reports.length === 0 && (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <ListIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            This list is empty
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Add reports from the Reports page to populate this list
          </Typography>
          <Button variant="outlined" onClick={() => navigate('/reports/social')}>
            Go to Reports
          </Button>
        </Card>
      )}
    </Box>
  );
};

export default ListDetail;
