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
  alpha,
  useTheme,
  Avatar,
  Stack,
  LinearProgress,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  CheckCircle as EnabledIcon,
  Cancel as DisabledIcon,
  RssFeed as RssIcon,
  Search as SearchIcon,
  TagOutlined as HashtagIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { feedsApi, type Feed } from '../api/feeds';
import { motion } from 'framer-motion';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Feeds: React.FC = () => {
  const theme = useTheme();
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
        return theme.palette.primary.main;
      case 'google_search':
        return theme.palette.success.main;
      case 'tiktok':
        return theme.palette.secondary.main;
      case 'instagram':
        return theme.palette.warning.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'rss':
        return <RssIcon />;
      case 'google_search':
        return <SearchIcon />;
      default:
        return <HashtagIcon />;
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
      feed_type: feedTypes[0].value,
      fetch_count: newProvider === 'GOOGLE_SEARCH' ? 10 : 30,
    });
  };

  const getSuccessRate = (feed: Feed) => {
    const total = feed.fetch_count_success + feed.fetch_count_failed;
    if (total === 0) return 0;
    return (feed.fetch_count_success / total) * 100;
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
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.light, 0.1)}, ${alpha(theme.palette.success.light, 0.1)})`,
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
            Feeds
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your news feeds and search queries
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
          size="large"
          sx={{ px: 3, py: 1.5 }}
        >
          Add Feed
        </Button>
      </MotionBox>

      {/* Feeds Grid */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {feeds?.map((feed: Feed, index: number) => {
          const successRate = getSuccessRate(feed);
          return (
            <MotionCard
              key={feed.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              sx={{
                '&:hover': {
                  transform: 'translateX(4px)',
                  boxShadow: `0 8px 24px ${alpha(getProviderColor(feed.provider), 0.15)}`,
                },
                transition: 'all 0.3s ease',
                borderLeft: `4px solid ${getProviderColor(feed.provider)}`,
                opacity: feed.enabled ? 1 : 0.6,
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                  <Box display="flex" gap={2} flex={1}>
                    <Avatar
                      sx={{
                        width: 56,
                        height: 56,
                        background: `linear-gradient(135deg, ${getProviderColor(feed.provider)}, ${alpha(getProviderColor(feed.provider), 0.7)})`,
                      }}
                    >
                      {getProviderIcon(feed.provider)}
                    </Avatar>

                    <Box flex={1}>
                      <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {feed.label || feed.feed_type}
                        </Typography>
                        <Chip
                          label={feed.provider}
                          size="small"
                          sx={{
                            backgroundColor: alpha(getProviderColor(feed.provider), 0.1),
                            color: getProviderColor(feed.provider),
                            fontWeight: 500,
                          }}
                        />
                        <Chip
                          icon={feed.enabled ? <EnabledIcon /> : <DisabledIcon />}
                          label={feed.enabled ? 'Enabled' : 'Disabled'}
                          color={feed.enabled ? 'success' : 'default'}
                          size="small"
                          sx={{ fontWeight: 500 }}
                        />
                      </Box>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                        sx={{
                          mb: 1.5,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          maxWidth: '600px',
                        }}
                      >
                        {feed.feed_value}
                      </Typography>

                      <Stack direction="row" spacing={3} alignItems="center">
                        <Box>
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                            Fetch Count
                          </Typography>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {feed.fetch_count}
                          </Typography>
                        </Box>

                        <Box flex={1}>
                          <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
                            <Typography variant="caption" color="text.secondary">
                              Fetch Success Rate
                            </Typography>
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>
                              {successRate.toFixed(1)}%
                            </Typography>
                          </Box>
                          <LinearProgress
                            variant="determinate"
                            value={successRate}
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              backgroundColor: alpha(theme.palette.success.main, 0.1),
                              '& .MuiLinearProgress-bar': {
                                backgroundColor: theme.palette.success.main,
                                borderRadius: 3,
                              },
                            }}
                          />
                        </Box>

                        <Stack direction="row" spacing={1}>
                          <Chip
                            label={`✓ ${feed.fetch_count_success}`}
                            size="small"
                            sx={{
                              backgroundColor: alpha(theme.palette.success.main, 0.1),
                              color: theme.palette.success.main,
                              fontWeight: 500,
                            }}
                          />
                          {feed.fetch_count_failed > 0 && (
                            <Chip
                              label={`✗ ${feed.fetch_count_failed}`}
                              size="small"
                              sx={{
                                backgroundColor: alpha(theme.palette.error.main, 0.1),
                                color: theme.palette.error.main,
                                fontWeight: 500,
                              }}
                            />
                          )}
                        </Stack>
                      </Stack>
                    </Box>
                  </Box>

                  <Stack direction="row" spacing={1}>
                    <IconButton
                      size="small"
                      onClick={() => handleOpen(feed)}
                      sx={{
                        color: theme.palette.primary.main,
                        '&:hover': {
                          backgroundColor: alpha(theme.palette.primary.main, 0.1),
                        },
                      }}
                    >
                      <EditIcon />
                    </IconButton>
                    <IconButton
                      size="small"
                      onClick={() => handleDelete(feed.id)}
                      sx={{
                        color: theme.palette.error.main,
                        '&:hover': {
                          backgroundColor: alpha(theme.palette.error.main, 0.1),
                        },
                      }}
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

      {feeds?.length === 0 && (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <RssIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No feeds configured
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Add your first feed to start tracking media mentions
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
            Add Feed
          </Button>
        </Card>
      )}

      {/* Add/Edit Dialog */}
      <Dialog
        open={open}
        onClose={handleClose}
        maxWidth="sm"
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
            {editingFeed ? 'Edit Feed' : 'Add Feed'}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          {!editingFeed && (
            <>
              <TextField
                fullWidth
                label="Provider"
                value={formData.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                margin="normal"
                select
                slotProps={{ select: { native: true } }}
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
                slotProps={{ select: { native: true } }}
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
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.enabled}
                  onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                />
              }
              label="Enabled"
            />
          </Box>
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

export default Feeds;
