import React from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Switch,
  TextField,
  Stack,
  Collapse,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Instagram as InstagramIcon,
  YouTube as YouTubeIcon,
  Newspaper as NewsIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import SearchEntryList from './SearchEntryList';
import type { ProviderConfig, ProviderMetadata, SearchEntry } from '../types';

// TikTok icon (custom SVG since MUI doesn't have it)
const TikTokIcon: React.FC<{ sx?: any }> = ({ sx }) => (
  <svg viewBox="0 0 24 24" width="1em" height="1em" style={sx}>
    <path
      fill="currentColor"
      d="M16.6 5.82s.51.5 0 0A4.278 4.278 0 0 1 15.54 3h-3.09v12.4a2.592 2.592 0 0 1-2.59 2.5c-1.42 0-2.6-1.16-2.6-2.6 0-1.72 1.66-3.01 3.37-2.48V9.66c-3.45-.46-6.47 2.22-6.47 5.64 0 3.33 2.76 5.7 5.69 5.7 3.14 0 5.69-2.55 5.69-5.7V9.01a7.35 7.35 0 0 0 4.3 1.38V7.3s-1.88.09-3.24-1.48z"
    />
  </svg>
);

interface ProviderCardProps {
  provider: ProviderMetadata;
  config: ProviderConfig;
  onChange: (config: ProviderConfig) => void;
  defaultSearchCount?: number;
  disabled?: boolean;
}

const ProviderCard: React.FC<ProviderCardProps> = ({
  provider,
  config,
  onChange,
  defaultSearchCount = 5,
  disabled = false,
}) => {
  const theme = useTheme();

  const getProviderIcon = () => {
    switch (provider.name) {
      case 'instagram':
        return <InstagramIcon sx={{ fontSize: 24 }} />;
      case 'tiktok':
        return <TikTokIcon sx={{ fontSize: 24 }} />;
      case 'youtube':
        return <YouTubeIcon sx={{ fontSize: 24 }} />;
      case 'google_news':
        return <NewsIcon sx={{ fontSize: 24 }} />;
      case 'google_search':
        return <SearchIcon sx={{ fontSize: 24 }} />;
      default:
        return <SearchIcon sx={{ fontSize: 24 }} />;
    }
  };

  const getProviderColor = () => {
    switch (provider.name) {
      case 'instagram':
        return '#E4405F';
      case 'tiktok':
        return '#000000';
      case 'youtube':
        return '#FF0000';
      case 'google_news':
        return '#4285F4';
      case 'google_search':
        return '#34A853';
      default:
        return theme.palette.primary.main;
    }
  };

  const handleToggle = () => {
    onChange({
      ...config,
      enabled: !config.enabled,
    });
  };

  const handleHandleChange = (handle: string) => {
    onChange({
      ...config,
      handle: handle.replace(/^@/, ''), // Remove @ if present
    });
  };

  const handleChannelIdChange = (channelId: string) => {
    onChange({
      ...config,
      channel_id: channelId,
    });
  };

  const handleChannelHandleChange = (channelHandle: string) => {
    onChange({
      ...config,
      channel_handle: channelHandle.replace(/^@/, ''),
    });
  };

  const handleSearchesChange = (searches: SearchEntry[]) => {
    onChange({
      ...config,
      searches,
    });
  };

  const providerColor = getProviderColor();

  return (
    <Card
      variant="outlined"
      sx={{
        borderColor: config.enabled ? providerColor : alpha(theme.palette.divider, 0.3),
        borderWidth: config.enabled ? 2 : 1,
        transition: 'all 0.2s ease',
        opacity: disabled ? 0.6 : 1,
      }}
    >
      <CardContent sx={{ pb: '16px !important' }}>
        {/* Header with icon, name, and toggle */}
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mb: config.enabled ? 2 : 0 }}
        >
          <Stack direction="row" alignItems="center" spacing={1.5}>
            <Box
              sx={{
                width: 40,
                height: 40,
                borderRadius: 1.5,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                bgcolor: alpha(providerColor, 0.1),
                color: providerColor,
              }}
            >
              {getProviderIcon()}
            </Box>
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                {provider.display_name}
              </Typography>
              {config.enabled && config.searches.length > 0 && (
                <Typography variant="caption" color="text.secondary">
                  {config.searches.length} search{config.searches.length !== 1 ? 'es' : ''} configured
                </Typography>
              )}
            </Box>
          </Stack>

          <Switch
            checked={config.enabled}
            onChange={handleToggle}
            disabled={disabled}
            sx={{
              '& .MuiSwitch-switchBase.Mui-checked': {
                color: providerColor,
              },
              '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                backgroundColor: providerColor,
              },
            }}
          />
        </Stack>

        {/* Expanded content when enabled */}
        <Collapse in={config.enabled}>
          <Stack spacing={2}>
            {/* Handle input for social media providers */}
            {provider.requires_handle && (
              <TextField
                size="small"
                label={provider.handle_label || 'Handle'}
                placeholder={provider.handle_placeholder || '@username'}
                value={config.handle || ''}
                onChange={(e) => handleHandleChange(e.target.value)}
                disabled={disabled}
                fullWidth
                slotProps={{
                  input: {
                    startAdornment: (
                      <Typography color="text.secondary" sx={{ mr: 0.5 }}>
                        @
                      </Typography>
                    ),
                  },
                }}
              />
            )}

            {/* YouTube-specific fields */}
            {provider.name === 'youtube' && (
              <Stack direction="row" spacing={2}>
                <TextField
                  size="small"
                  label="Channel ID"
                  placeholder="UCxxxxxxxxxx"
                  value={config.channel_id || ''}
                  onChange={(e) => handleChannelIdChange(e.target.value)}
                  disabled={disabled}
                  sx={{ flex: 1 }}
                  helperText="Required for channel searches"
                />
                <TextField
                  size="small"
                  label="Channel Handle"
                  placeholder="@channelname"
                  value={config.channel_handle || ''}
                  onChange={(e) => handleChannelHandleChange(e.target.value)}
                  disabled={disabled}
                  sx={{ flex: 1 }}
                  slotProps={{
                    input: {
                      startAdornment: (
                        <Typography color="text.secondary" sx={{ mr: 0.5 }}>
                          @
                        </Typography>
                      ),
                    },
                  }}
                />
              </Stack>
            )}

            {/* Search entries */}
            <Box>
              <Typography
                variant="body2"
                fontWeight={500}
                color="text.secondary"
                sx={{ mb: 1 }}
              >
                Searches
              </Typography>
              <SearchEntryList
                entries={config.searches || []}
                searchTypes={provider.search_types}
                onChange={handleSearchesChange}
                defaultCount={defaultSearchCount}
                disabled={disabled}
              />
            </Box>
          </Stack>
        </Collapse>
      </CardContent>
    </Card>
  );
};

export default ProviderCard;
