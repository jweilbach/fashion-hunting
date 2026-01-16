import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  IconButton,
  Chip,
  Stack,
  alpha,
  useTheme,
  Skeleton,
  Tooltip,
} from '@mui/material';
import {
  PictureAsPdf as PdfIcon,
  Download as DownloadIcon,
  Delete as DeleteIcon,
  ErrorOutline as ErrorIcon,
  Schedule as PendingIcon,
  Autorenew as GeneratingIcon,
} from '@mui/icons-material';
import type { Summary } from '../types';

interface SummaryListProps {
  summaries: Summary[];
  compact?: boolean;
  loading?: boolean;
  onDownload?: (summaryId: string) => void;
  onDelete?: (summaryId: string) => void;
  showDelete?: boolean;
}

const SummaryList: React.FC<SummaryListProps> = ({
  summaries,
  compact = false,
  loading = false,
  onDownload,
  onDelete,
  showDelete = false,
}) => {
  const theme = useTheme();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'generating':
        return 'info';
      case 'pending':
        return 'warning';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <PdfIcon fontSize="small" />;
      case 'generating':
        return <GeneratingIcon fontSize="small" sx={{ animation: 'spin 2s linear infinite' }} />;
      case 'pending':
        return <PendingIcon fontSize="small" />;
      case 'failed':
        return <ErrorIcon fontSize="small" />;
      default:
        return <PdfIcon fontSize="small" />;
    }
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (loading) {
    return (
      <Stack spacing={compact ? 1 : 2}>
        {[1, 2, 3].map((i) => (
          <Card key={i} variant="outlined">
            <CardContent sx={{ py: compact ? 1.5 : 2 }}>
              <Stack direction="row" spacing={2} alignItems="center">
                <Skeleton variant="circular" width={40} height={40} />
                <Box sx={{ flex: 1 }}>
                  <Skeleton variant="text" width="60%" />
                  <Skeleton variant="text" width="40%" />
                </Box>
              </Stack>
            </CardContent>
          </Card>
        ))}
      </Stack>
    );
  }

  if (summaries.length === 0) {
    return (
      <Box
        sx={{
          textAlign: 'center',
          py: compact ? 3 : 6,
          color: 'text.secondary',
        }}
      >
        <PdfIcon sx={{ fontSize: 48, opacity: 0.3, mb: 1 }} />
        <Typography variant="body2">No summaries yet</Typography>
      </Box>
    );
  }

  return (
    <Stack spacing={compact ? 1 : 2}>
      {summaries.map((summary) => (
        <Card
          key={summary.id}
          variant="outlined"
          sx={{
            transition: 'all 0.2s ease',
            '&:hover': {
              borderColor: theme.palette.primary.main,
              boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.15)}`,
            },
          }}
        >
          <CardContent sx={{ py: compact ? 1.5 : 2, '&:last-child': { pb: compact ? 1.5 : 2 } }}>
            <Stack direction="row" spacing={2} alignItems="center">
              {/* PDF Icon with Status */}
              <Box
                sx={{
                  width: compact ? 36 : 44,
                  height: compact ? 36 : 44,
                  borderRadius: 2,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  bgcolor: alpha(theme.palette.error.main, 0.1),
                  color: theme.palette.error.main,
                }}
              >
                <PdfIcon sx={{ fontSize: compact ? 20 : 24 }} />
              </Box>

              {/* Summary Info */}
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography
                  variant={compact ? 'body2' : 'subtitle1'}
                  fontWeight={600}
                  noWrap
                  sx={{ mb: 0.5 }}
                >
                  {summary.title}
                </Typography>

                <Stack
                  direction="row"
                  spacing={1}
                  alignItems="center"
                  flexWrap="wrap"
                  useFlexGap
                >
                  <Chip
                    size="small"
                    icon={getStatusIcon(summary.generation_status)}
                    label={summary.generation_status}
                    color={getStatusColor(summary.generation_status) as any}
                    sx={{ height: 24, fontSize: '0.75rem' }}
                  />

                  {summary.report_count > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      {summary.report_count} reports
                    </Typography>
                  )}

                  {summary.file_size_bytes && summary.generation_status === 'completed' && (
                    <Typography variant="caption" color="text.secondary">
                      {formatFileSize(summary.file_size_bytes)}
                    </Typography>
                  )}

                  {summary.created_at && (
                    <Typography variant="caption" color="text.secondary">
                      {formatDate(summary.created_at)}
                    </Typography>
                  )}
                </Stack>

                {/* Period info - only in non-compact mode */}
                {!compact && summary.period_start && summary.period_end && (
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
                    {formatDate(summary.period_start)} - {formatDate(summary.period_end)}
                  </Typography>
                )}

                {/* Error message - only if failed */}
                {summary.generation_status === 'failed' && summary.generation_error && (
                  <Typography
                    variant="caption"
                    color="error"
                    sx={{
                      mt: 0.5,
                      display: 'block',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {summary.generation_error}
                  </Typography>
                )}
              </Box>

              {/* Actions */}
              <Stack direction="row" spacing={0.5}>
                {summary.generation_status === 'completed' && onDownload && (
                  <Tooltip title="Download PDF">
                    <IconButton
                      size={compact ? 'small' : 'medium'}
                      onClick={() => onDownload(summary.id)}
                      sx={{
                        color: theme.palette.primary.main,
                        '&:hover': {
                          bgcolor: alpha(theme.palette.primary.main, 0.1),
                        },
                      }}
                    >
                      <DownloadIcon fontSize={compact ? 'small' : 'medium'} />
                    </IconButton>
                  </Tooltip>
                )}

                {showDelete && onDelete && (
                  <Tooltip title="Delete summary">
                    <IconButton
                      size={compact ? 'small' : 'medium'}
                      onClick={() => onDelete(summary.id)}
                      sx={{
                        color: theme.palette.text.secondary,
                        '&:hover': {
                          bgcolor: alpha(theme.palette.error.main, 0.1),
                          color: theme.palette.error.main,
                        },
                      }}
                    >
                      <DeleteIcon fontSize={compact ? 'small' : 'medium'} />
                    </IconButton>
                  </Tooltip>
                )}
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      ))}

      {/* CSS for spinning animation */}
      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
    </Stack>
  );
};

export default SummaryList;
