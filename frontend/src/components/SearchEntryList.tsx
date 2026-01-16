import React from 'react';
import {
  Box,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  IconButton,
  Button,
  Stack,
  Typography,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Delete as DeleteIcon,
  Add as AddIcon,
} from '@mui/icons-material';
import type { SearchEntry, SearchTypeOption } from '../types';

interface SearchEntryListProps {
  entries: SearchEntry[];
  searchTypes: SearchTypeOption[];
  onChange: (entries: SearchEntry[]) => void;
  defaultCount?: number;
  maxCount?: number;
  disabled?: boolean;
}

const SearchEntryList: React.FC<SearchEntryListProps> = ({
  entries,
  searchTypes,
  onChange,
  defaultCount = 5,
  maxCount = 100,
  disabled = false,
}) => {
  const theme = useTheme();

  const handleAddEntry = () => {
    const defaultType = searchTypes[0]?.value || '';
    onChange([
      ...entries,
      { type: defaultType, value: '', count: defaultCount },
    ]);
  };

  const handleRemoveEntry = (index: number) => {
    const newEntries = entries.filter((_, i) => i !== index);
    onChange(newEntries);
  };

  const handleUpdateEntry = (index: number, field: keyof SearchEntry, value: string | number) => {
    const newEntries = entries.map((entry, i) => {
      if (i === index) {
        return { ...entry, [field]: value };
      }
      return entry;
    });
    onChange(newEntries);
  };

  const getPlaceholder = (type: string) => {
    switch (type) {
      case 'hashtag':
        return 'e.g., fashion';
      case 'profile':
      case 'user':
        return 'e.g., nike';
      case 'mentions':
        return 'e.g., nike';
      case 'keyword':
        return 'e.g., summer trends';
      case 'channel':
        return 'e.g., UCxxxxxxxxxx';
      case 'search':
        return 'e.g., brand name';
      case 'video':
        return 'Video ID';
      case 'rss_keyword':
        return 'e.g., Nike news';
      default:
        return 'Enter value';
    }
  };

  if (searchTypes.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 2, textAlign: 'center' }}>
        No search types available for this provider
      </Typography>
    );
  }

  return (
    <Box>
      <Stack spacing={1.5}>
        {entries.map((entry, index) => (
          <Stack
            key={index}
            direction="row"
            spacing={1}
            alignItems="center"
            sx={{
              p: 1.5,
              borderRadius: 1,
              bgcolor: alpha(theme.palette.background.default, 0.5),
              border: `1px solid ${alpha(theme.palette.divider, 0.3)}`,
            }}
          >
            {/* Search Type Dropdown */}
            <FormControl size="small" sx={{ minWidth: 110 }}>
              <InputLabel>Type</InputLabel>
              <Select
                value={entry.type}
                label="Type"
                onChange={(e) => handleUpdateEntry(index, 'type', e.target.value)}
                disabled={disabled}
              >
                {searchTypes.map((st) => (
                  <MenuItem key={st.value} value={st.value}>
                    {st.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Value Input */}
            <TextField
              size="small"
              value={entry.value}
              onChange={(e) => handleUpdateEntry(index, 'value', e.target.value)}
              placeholder={getPlaceholder(entry.type)}
              disabled={disabled}
              sx={{ flex: 1, minWidth: 120 }}
            />

            {/* Count Input */}
            <TextField
              size="small"
              type="number"
              value={entry.count}
              onChange={(e) => {
                const val = parseInt(e.target.value) || defaultCount;
                handleUpdateEntry(index, 'count', Math.min(maxCount, Math.max(1, val)));
              }}
              label="Count"
              disabled={disabled}
              slotProps={{ htmlInput: { min: 1, max: maxCount } }}
              sx={{ width: 80 }}
            />

            {/* Delete Button */}
            <IconButton
              size="small"
              onClick={() => handleRemoveEntry(index)}
              disabled={disabled}
              sx={{
                color: theme.palette.text.secondary,
                '&:hover': {
                  bgcolor: alpha(theme.palette.error.main, 0.1),
                  color: theme.palette.error.main,
                },
              }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
          </Stack>
        ))}
      </Stack>

      {/* Add Search Button */}
      <Button
        size="small"
        startIcon={<AddIcon />}
        onClick={handleAddEntry}
        disabled={disabled}
        sx={{ mt: 1.5 }}
      >
        Add Search
      </Button>
    </Box>
  );
};

export default SearchEntryList;
