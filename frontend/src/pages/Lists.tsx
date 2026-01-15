import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
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
  alpha,
  useTheme,
  Avatar,
  Stack,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  List as ListIcon,
  Download as DownloadIcon,
  OpenInNew as OpenIcon,
  MoreVert as MoreIcon,
  Description as ReportIcon,
  Person as ContactIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listsApi } from '../api/lists';
import { motion } from 'framer-motion';
import type { List, ListCreate } from '../types';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Lists: React.FC = () => {
  const theme = useTheme();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [editingList, setEditingList] = useState<List | null>(null);
  const [formData, setFormData] = useState<ListCreate>({
    name: '',
    list_type: 'report',
    description: '',
  });
  const [menuAnchor, setMenuAnchor] = useState<{ el: HTMLElement; list: List } | null>(null);

  const queryClient = useQueryClient();

  const { data: listsData, isLoading, error } = useQuery({
    queryKey: ['lists'],
    queryFn: () => listsApi.getLists(),
  });

  // Fetch supported list types from API
  const { data: listTypesData } = useQuery({
    queryKey: ['listTypes'],
    queryFn: () => listsApi.getListTypes(),
  });

  const supportedListTypes = listTypesData?.types || [];

  const createMutation = useMutation({
    mutationFn: (data: ListCreate) => listsApi.createList(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists'] });
      handleClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ListCreate> }) =>
      listsApi.updateList(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists'] });
      handleClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => listsApi.deleteList(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['lists'] });
    },
  });

  const handleOpen = (list?: List) => {
    if (list) {
      setEditingList(list);
      setFormData({
        name: list.name,
        list_type: list.list_type,
        description: list.description || '',
      });
    } else {
      setEditingList(null);
      setFormData({
        name: '',
        list_type: 'report',
        description: '',
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingList(null);
  };

  const handleSubmit = () => {
    if (editingList) {
      updateMutation.mutate({
        id: editingList.id,
        data: {
          name: formData.name,
          description: formData.description,
        },
      });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this list? All items will be removed.')) {
      deleteMutation.mutate(id);
    }
    setMenuAnchor(null);
  };

  const handleExport = async (list: List, format: 'csv' | 'excel') => {
    try {
      await listsApi.exportList(list.id, format);
    } catch (err) {
      console.error('Export failed:', err);
    }
    setMenuAnchor(null);
  };

  const handleViewList = (list: List) => {
    navigate(`/lists/${list.id}`);
  };

  const getListTypeIcon = (listType: string) => {
    switch (listType) {
      case 'report':
        return <ReportIcon />;
      case 'contact':
        return <ContactIcon />;
      default:
        return <ListIcon />;
    }
  };

  const getListTypeColor = (listType: string) => {
    switch (listType) {
      case 'report':
        return theme.palette.primary.main;
      case 'contact':
        return theme.palette.success.main;
      case 'editor':
        return theme.palette.warning.main;
      default:
        return theme.palette.info.main;
    }
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
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
    return <Alert severity="error">Failed to load lists. Please try again later.</Alert>;
  }

  const lists = listsData?.items || [];

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
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Box>
          <Typography variant="h3" gutterBottom sx={{ fontWeight: 600, mb: 1 }}>
            Lists
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Organize and export your reports into custom lists
          </Typography>
        </Box>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
          size="large"
          sx={{
            px: 3,
            py: 1.5,
          }}
        >
          Create List
        </Button>
      </MotionBox>

      {/* Lists Grid */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {lists.map((list: List, index: number) => {
          const typeColor = getListTypeColor(list.list_type);

          return (
            <MotionCard
              key={list.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              sx={{
                cursor: 'pointer',
                '&:hover': {
                  transform: 'translateX(4px)',
                  boxShadow: `0 8px 24px ${alpha(typeColor, 0.15)}`,
                },
                transition: 'all 0.3s ease',
                borderLeft: `4px solid ${typeColor}`,
              }}
              onClick={() => handleViewList(list)}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                  <Box display="flex" gap={2} flex={1}>
                    <Avatar
                      sx={{
                        width: 56,
                        height: 56,
                        background: `linear-gradient(135deg, ${typeColor}, ${alpha(typeColor, 0.7)})`,
                        fontSize: '1.5rem',
                        fontWeight: 600,
                      }}
                    >
                      {getListTypeIcon(list.list_type)}
                    </Avatar>

                    <Box flex={1}>
                      <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                        <Typography variant="h6" sx={{ fontWeight: 600 }}>
                          {list.name}
                        </Typography>
                        <Chip
                          label={`${list.item_count} items`}
                          size="small"
                          sx={{
                            backgroundColor: alpha(typeColor, 0.1),
                            color: typeColor,
                            fontWeight: 500,
                          }}
                        />
                        <Chip
                          label={list.list_type}
                          size="small"
                          variant="outlined"
                          sx={{ textTransform: 'capitalize' }}
                        />
                      </Box>

                      {list.description && (
                        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                          {list.description}
                        </Typography>
                      )}

                      <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          Created: {formatDate(list.created_at)}
                        </Typography>
                        {list.creator_name && (
                          <Typography variant="caption" color="text.secondary">
                            By: {list.creator_name}
                          </Typography>
                        )}
                        <Typography variant="caption" color="text.secondary">
                          Updated: {formatDate(list.updated_at)}
                        </Typography>
                      </Stack>
                    </Box>
                  </Box>

                  <Stack direction="row" spacing={1} onClick={(e) => e.stopPropagation()}>
                    <Tooltip title="View List">
                      <IconButton
                        size="small"
                        onClick={() => handleViewList(list)}
                        sx={{
                          color: theme.palette.primary.main,
                          '&:hover': {
                            backgroundColor: alpha(theme.palette.primary.main, 0.1),
                          },
                        }}
                      >
                        <OpenIcon />
                      </IconButton>
                    </Tooltip>
                    <IconButton
                      size="small"
                      onClick={(e) => setMenuAnchor({ el: e.currentTarget, list })}
                      sx={{
                        '&:hover': {
                          backgroundColor: alpha(theme.palette.text.primary, 0.1),
                        },
                      }}
                    >
                      <MoreIcon />
                    </IconButton>
                  </Stack>
                </Box>
              </CardContent>
            </MotionCard>
          );
        })}
      </Box>

      {lists.length === 0 && (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <ListIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No lists yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Create your first list to organize reports
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
            Create List
          </Button>
        </Card>
      )}

      {/* Context Menu */}
      <Menu
        anchorEl={menuAnchor?.el}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem onClick={() => menuAnchor && handleOpen(menuAnchor.list)}>
          <EditIcon sx={{ mr: 1 }} fontSize="small" />
          Edit
        </MenuItem>
        <MenuItem onClick={() => menuAnchor && handleExport(menuAnchor.list, 'csv')}>
          <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
          Export CSV
        </MenuItem>
        <MenuItem onClick={() => menuAnchor && handleExport(menuAnchor.list, 'excel')}>
          <DownloadIcon sx={{ mr: 1 }} fontSize="small" />
          Export Excel
        </MenuItem>
        <MenuItem
          onClick={() => menuAnchor && handleDelete(menuAnchor.list.id)}
          sx={{ color: theme.palette.error.main }}
        >
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          Delete
        </MenuItem>
      </Menu>

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
            {editingList ? 'Edit List' : 'Create List'}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="List Name"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            margin="normal"
            required
          />
          {!editingList && (
            <TextField
              fullWidth
              label="List Type"
              value={formData.list_type}
              onChange={(e) => setFormData({ ...formData, list_type: e.target.value as any })}
              margin="normal"
              select
              slotProps={{ select: { native: true } }}
            >
              {supportedListTypes.map((type) => (
                <option key={type.id} value={type.id}>{type.label}</option>
              ))}
            </TextField>
          )}
          <TextField
            fullWidth
            label="Description"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
        </DialogContent>
        <DialogActions sx={{ p: 3, pt: 2 }}>
          <Button onClick={handleClose} size="large">
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
            size="large"
            disabled={!formData.name || createMutation.isPending || updateMutation.isPending}
          >
            {editingList ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Lists;
