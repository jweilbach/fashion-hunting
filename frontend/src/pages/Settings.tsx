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
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  CheckCircle as EnabledIcon,
  Cancel as DisabledIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { feedsApi, type Feed } from '../api/feeds';

const Settings: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [editingFeed, setEditingFeed] = useState<Feed | null>(null);
  const [formData, setFormData] = useState({
    provider: 'RSS',
    feed_type: 'rss_url',
    feed_value: '',
    label: '',
    enabled: true,
    fetch_count: 30,
  });

  const queryClient = useQueryClient();

  const { data: feeds, isLoading, error } = useQuery({
    queryKey: ['feeds'],
    queryFn: () => feedsApi.getFeeds(),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => feedsApi.createFeed(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
      handleClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      feedsApi.updateFeed(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
      handleClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => feedsApi.deleteFeed(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['feeds'] });
    },
  });

  const handleOpen = (feed?: Feed) => {
    if (feed) {
      setEditingFeed(feed);
      setFormData({
        provider: feed.provider,
        feed_type: feed.feed_type,
        feed_value: feed.feed_value,
        label: feed.label || '',
        enabled: feed.enabled,
        fetch_count: feed.fetch_count,
      });
    } else {
      setEditingFeed(null);
      setFormData({
        provider: 'RSS',
        feed_type: 'rss_url',
        feed_value: '',
        label: '',
        enabled: true,
        fetch_count: 30,
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingFeed(null);
  };

  const handleSubmit = () => {
    let feedValue = formData.feed_value;
    let feedType = formData.feed_type;

    // If RSS feed and feed_type is keyword, convert to Google News RSS URL
    if (!editingFeed && formData.provider === 'RSS' && formData.feed_type === 'keyword') {
      const encodedQuery = encodeURIComponent(formData.feed_value);
      feedValue = `https://news.google.com/rss/search?q=${encodedQuery}`;
      feedType = 'rss_url';
    }

    const submitData = {
      provider: formData.provider,
      feed_type: feedType,
      feed_value: feedValue,
      label: formData.label || undefined,
      enabled: formData.enabled,
      fetch_count: formData.fetch_count,
    };

    if (editingFeed) {
      // For update, only send fields that can be updated
      const updateData = {
        label: formData.label || undefined,
        enabled: formData.enabled,
        fetch_count: formData.fetch_count,
      };
      updateMutation.mutate({ id: editingFeed.id, data: updateData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this feed?')) {
      deleteMutation.mutate(id);
    }
  };

  const getProviderColor = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'rss':
        return 'primary';
      case 'google_search':
        return 'success';
      case 'tiktok':
        return 'secondary';
      case 'instagram':
        return 'warning';
      default:
        return 'default';
    }
  };

  const getFeedTypesForProvider = (provider: string): { value: string; label: string }[] => {
    switch (provider) {
      case 'RSS':
        return [
          { value: 'rss_url', label: 'RSS URL' },
          { value: 'keyword', label: 'Keyword (Google News)' },
        ];
      case 'GOOGLE_SEARCH':
        return [
          { value: 'brand_search', label: 'Brand Search' },
          { value: 'keyword_search', label: 'Keyword Search' },
        ];
      case 'TikTok':
        return [
          { value: 'hashtag', label: 'Hashtag' },
          { value: 'keyword', label: 'Keyword' },
          { value: 'user', label: 'User/Account' },
        ];
      case 'Instagram':
        return [
          { value: 'hashtag', label: 'Hashtag' },
          { value: 'keyword', label: 'Keyword' },
          { value: 'user', label: 'User/Account' },
        ];
      default:
        return [{ value: 'rss_url', label: 'RSS URL' }];
    }
  };

  const handleProviderChange = (newProvider: string) => {
    const feedTypes = getFeedTypesForProvider(newProvider);
    setFormData({
      ...formData,
      provider: newProvider,
      feed_type: feedTypes[0].value, // Set to first available feed type
      fetch_count: newProvider === 'GOOGLE_SEARCH' ? 10 : 30, // Default 10 for Google Search, 30 for others
    });
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load feeds. Please try again later.</Alert>;
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h3">Feeds</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
        >
          Add Feed
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Provider</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Feed URL/Value</TableCell>
              <TableCell>Label</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Fetch Count</TableCell>
              <TableCell>Stats</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {feeds?.map((feed: Feed) => (
              <TableRow key={feed.id}>
                <TableCell>
                  <Chip label={feed.provider} color={getProviderColor(feed.provider)} size="small" />
                </TableCell>
                <TableCell>{feed.feed_type}</TableCell>
                <TableCell sx={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {feed.feed_value}
                </TableCell>
                <TableCell>{feed.label || '-'}</TableCell>
                <TableCell>
                  {feed.enabled ? (
                    <Chip icon={<EnabledIcon />} label="Enabled" color="success" size="small" />
                  ) : (
                    <Chip icon={<DisabledIcon />} label="Disabled" color="default" size="small" />
                  )}
                </TableCell>
                <TableCell>{feed.fetch_count}</TableCell>
                <TableCell>
                  <Typography variant="caption" color="success.main">
                    ✓ {feed.fetch_count_success}
                  </Typography>
                  {feed.fetch_count_failed > 0 && (
                    <>
                      {' / '}
                      <Typography variant="caption" color="error.main">
                        ✗ {feed.fetch_count_failed}
                      </Typography>
                    </>
                  )}
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => handleOpen(feed)}
                    color="primary"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(feed.id)}
                    color="error"
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
      <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
        <DialogTitle>{editingFeed ? 'Edit Feed' : 'Add Feed'}</DialogTitle>
        <DialogContent>
          {!editingFeed && (
            <>
              <TextField
                fullWidth
                label="Provider"
                value={formData.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                margin="normal"
                select
                SelectProps={{ native: true }}
                required
              >
                <option value="RSS">RSS</option>
                <option value="GOOGLE_SEARCH">Google Search</option>
                <option value="TikTok">TikTok</option>
                <option value="Instagram">Instagram</option>
              </TextField>
              <TextField
                fullWidth
                label="Feed Type"
                value={formData.feed_type}
                onChange={(e) => setFormData({ ...formData, feed_type: e.target.value })}
                margin="normal"
                select
                SelectProps={{ native: true }}
                required
              >
                {getFeedTypesForProvider(formData.provider).map((feedType) => (
                  <option key={feedType.value} value={feedType.value}>
                    {feedType.label}
                  </option>
                ))}
              </TextField>
              <TextField
                fullWidth
                label={formData.provider === 'GOOGLE_SEARCH' ? 'Search Query' : 'Feed URL/Value'}
                value={formData.feed_value}
                onChange={(e) => setFormData({ ...formData, feed_value: e.target.value })}
                margin="normal"
                required
                helperText={
                  formData.provider === 'GOOGLE_SEARCH'
                    ? 'Search query (e.g., "Versace news", "luxury fashion collaboration")'
                    : 'RSS URL, hashtag, keyword, or username'
                }
              />
            </>
          )}
          {editingFeed && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Provider, type, and value cannot be changed for existing feeds. Create a new feed if needed.
            </Alert>
          )}
          <TextField
            fullWidth
            label="Label (optional)"
            value={formData.label}
            onChange={(e) => setFormData({ ...formData, label: e.target.value })}
            margin="normal"
            helperText="A friendly name for this feed"
          />
          <TextField
            fullWidth
            label="Fetch Count"
            type="number"
            value={formData.fetch_count}
            onChange={(e) => setFormData({ ...formData, fetch_count: parseInt(e.target.value) || 30 })}
            margin="normal"
            helperText={
              formData.provider === 'GOOGLE_SEARCH'
                ? 'Results per query (max 10, uses API quota)'
                : 'Number of items to fetch per run'
            }
            slotProps={{
              htmlInput: formData.provider === 'GOOGLE_SEARCH' ? { min: 1, max: 10 } : {}
            }}
          />
          <FormControlLabel
            control={
              <Switch
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              />
            }
            label="Enabled"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            disabled={
              (!editingFeed && (!formData.feed_value || !formData.provider || !formData.feed_type)) ||
              createMutation.isPending ||
              updateMutation.isPending
            }
          >
            {editingFeed ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Settings;
