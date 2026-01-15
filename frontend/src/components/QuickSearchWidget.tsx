import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Select,
  MenuItem,
  Button,
  FormControl,
  InputLabel,
  Typography,
  CircularProgress,
  LinearProgress,
  Alert,
  Collapse,
  IconButton,
  Stack,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Search as SearchIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  CheckCircle as CheckIcon,
} from '@mui/icons-material';
import apiClient from '../api/client';

interface QuickSearchWidgetProps {
  onSearchComplete?: (result: any) => void;
}

interface ProgressState {
  stage: string;
  message: string;
  progress: number;
  current_item: number;
  total_items: number;
}

const QuickSearchWidget: React.FC<QuickSearchWidgetProps> = ({ onSearchComplete }) => {
  const theme = useTheme();
  const [expanded, setExpanded] = useState(true);
  const [providerType, setProviderType] = useState('INSTAGRAM');
  const [searchType, setSearchType] = useState('hashtag');
  const [searchValue, setSearchValue] = useState('');
  const [resultCount, setResultCount] = useState(10);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [, setTaskId] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Provider type options
  const providerOptions = [
    { value: 'INSTAGRAM', label: 'Instagram', defaultType: 'hashtag' },
    { value: 'TIKTOK', label: 'TikTok', defaultType: 'hashtag' },
    { value: 'YOUTUBE', label: 'YouTube', defaultType: 'search' },
    { value: 'GOOGLE_SEARCH', label: 'Google Search', defaultType: 'search' },
    { value: 'RSS', label: 'RSS Feed', defaultType: 'url' },
  ];

  // Search type options based on provider
  const getSearchTypeOptions = () => {
    switch (providerType) {
      case 'INSTAGRAM':
        return [
          { value: 'hashtag', label: 'Hashtag' },
          { value: 'profile', label: 'Profile' },
          { value: 'mentions', label: 'Mentions' },
        ];
      case 'TIKTOK':
        return [
          { value: 'hashtag', label: 'Hashtag' },
          { value: 'keyword', label: 'Keyword' },
          { value: 'user', label: 'User' },
        ];
      case 'YOUTUBE':
        return [
          { value: 'search', label: 'Search' },
          { value: 'channel', label: 'Channel' },
          { value: 'video', label: 'Video ID' },
        ];
      case 'GOOGLE_SEARCH':
        return [{ value: 'search', label: 'Search Query' }];
      case 'RSS':
        return [{ value: 'url', label: 'Feed URL' }];
      default:
        return [{ value: 'search', label: 'Search' }];
    }
  };

  const handleProviderChange = (newProvider: string) => {
    setProviderType(newProvider);
    // Auto-set search type based on provider
    const provider = providerOptions.find(p => p.value === newProvider);
    if (provider) {
      setSearchType(provider.defaultType);
    }
  };

  const pollTaskStatus = async (taskId: string) => {
    try {
      const response = await apiClient.get(`/api/v1/quick-search/status/${taskId}`);
      const data = response.data;

      if (data.status === 'running') {
        // Update progress
        setProgress({
          stage: data.stage || 'processing',
          message: data.message || 'Processing...',
          progress: data.progress || 0,
          current_item: data.current_item || 0,
          total_items: data.total_items || 0,
        });
      } else if (data.status === 'completed') {
        // Task complete
        setProgress({
          stage: 'completed',
          message: 'Complete',
          progress: 100,
          current_item: 0,
          total_items: 0,
        });
        setResult(data.result);
        setLoading(false);
        setTaskId(null);

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }

        if (onSearchComplete) {
          onSearchComplete(data.result);
        }
      } else if (data.status === 'failed') {
        // Task failed
        setError(data.message || 'Search failed');
        setLoading(false);
        setTaskId(null);

        if (pollIntervalRef.current) {
          clearInterval(pollIntervalRef.current);
          pollIntervalRef.current = null;
        }
      }
    } catch (err: any) {
      console.error('Error polling task status:', err);
    }
  };

  const handleSearch = async () => {
    if (!searchValue.trim()) {
      setError('Please enter a search term');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setProgress(null);

    try {
      // Start async task
      const response = await apiClient.post(
        '/api/v1/quick-search/execute-async',
        {
          provider_type: providerType,
          search_value: searchValue.trim(),
          search_type: searchType,
          result_count: resultCount,
        }
      );

      const newTaskId = response.data.task_id;
      setTaskId(newTaskId);

      // Start polling for progress
      pollIntervalRef.current = setInterval(() => {
        pollTaskStatus(newTaskId);
      }, 500); // Poll every 500ms

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Search failed. Please try again.');
      console.error('Quick search error:', err);
      setLoading(false);
    }
  };

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !loading) {
      handleSearch();
    }
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" component="h2">
            Quick Search
          </Typography>
          <IconButton
            onClick={() => setExpanded(!expanded)}
            size="small"
            aria-label={expanded ? 'collapse' : 'expand'}
          >
            {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>

        <Collapse in={expanded}>
          <Stack direction="row" spacing={2} flexWrap="wrap" useFlexGap>
            {/* Provider Type */}
            <FormControl size="small" sx={{ minWidth: 150, flex: '1 1 auto' }}>
              <InputLabel>Provider</InputLabel>
              <Select
                value={providerType}
                label="Provider"
                onChange={(e) => handleProviderChange(e.target.value)}
                disabled={loading}
              >
                {providerOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Search Type */}
            <FormControl size="small" sx={{ minWidth: 120, flex: '0 1 auto' }}>
              <InputLabel>Type</InputLabel>
              <Select
                value={searchType}
                label="Type"
                onChange={(e) => setSearchType(e.target.value)}
                disabled={loading}
              >
                {getSearchTypeOptions().map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Search Value */}
            <TextField
              size="small"
              label={`Enter ${searchType}`}
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyDown={handleKeyPress}
              disabled={loading}
              placeholder={
                searchType === 'hashtag'
                  ? 'skincare'
                  : searchType === 'url'
                  ? 'https://...'
                  : 'Search term'
              }
              sx={{ minWidth: 200, flex: '2 1 auto' }}
            />

            {/* Result Count */}
            <TextField
              size="small"
              type="number"
              label="Count"
              value={resultCount}
              onChange={(e) => setResultCount(Math.min(50, Math.max(1, parseInt(e.target.value) || 10)))}
              disabled={loading}
              slotProps={{ htmlInput: { min: 1, max: 50 } }}
              sx={{ width: 80, flex: '0 0 auto' }}
            />

            {/* Search Button */}
            <Button
              variant="contained"
              color="primary"
              onClick={handleSearch}
              disabled={loading || !searchValue.trim()}
              startIcon={loading ? <CircularProgress size={20} /> : <SearchIcon />}
              sx={{ minWidth: 120, flex: '0 0 auto' }}
            >
              {loading ? 'Searching...' : 'Search'}
            </Button>
          </Stack>

          {/* Determinate Progress Bar with Item Tracking */}
          {loading && progress && progress.total_items > 0 && (
            <Box sx={{ mt: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                <Typography variant="caption" color="text.secondary">
                  {progress.message}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                  {progress.current_item} / {progress.total_items}
                </Typography>
              </Box>
              <LinearProgress
                variant="determinate"
                value={progress.total_items > 0 ? (progress.current_item / progress.total_items) * 100 : progress.progress}
                sx={{
                  height: 6,
                  borderRadius: 1,
                  backgroundColor: alpha(theme.palette.primary.main, 0.2),
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 1,
                    backgroundColor: theme.palette.primary.main,
                  },
                }}
              />
            </Box>
          )}

          {/* Simple progress bar (shown before item tracking starts) */}
          {loading && (!progress || progress.total_items === 0) && (
            <Box sx={{ mt: 3 }}>
              <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                <Typography variant="caption" color="text.secondary">
                  {progress?.message || 'Starting search...'}
                </Typography>
                {progress && progress.progress > 0 && (
                  <Typography variant="caption" color="primary" sx={{ fontWeight: 600 }}>
                    {progress.progress}%
                  </Typography>
                )}
              </Box>
              <LinearProgress
                variant={progress && progress.progress > 0 ? 'determinate' : 'indeterminate'}
                value={progress?.progress || 0}
                sx={{
                  height: 6,
                  borderRadius: 1,
                  backgroundColor: alpha(theme.palette.primary.main, 0.2),
                  '& .MuiLinearProgress-bar': {
                    borderRadius: 1,
                    backgroundColor: theme.palette.primary.main,
                  },
                }}
              />
            </Box>
          )}

          {/* Error Message */}
          {error && (
            <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          {/* Success Message */}
          {result && !loading && (
            <Alert
              severity="success"
              sx={{ mt: 2 }}
              iconMapping={{
                success: <CheckIcon fontSize="inherit" />,
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 500 }}>
                Found {result.items_fetched} items, created {result.reports_created} reports
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Check the Recent Mentions section below to see results!
              </Typography>
            </Alert>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default QuickSearchWidget;
