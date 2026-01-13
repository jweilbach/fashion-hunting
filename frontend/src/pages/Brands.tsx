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
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Add as AddIcon,
  Business as BusinessIcon,
  CheckCircle as KnownIcon,
  Warning as UnknownIcon,
  BlockOutlined as IgnoredIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { brandsApi } from '../api/brands';
import { motion } from 'framer-motion';
import type { Brand as ApiBrand } from '../types';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

interface BrandWithExtras extends ApiBrand {
  aliases?: string[];
  should_ignore?: boolean;
  notes?: string;
}

type Brand = BrandWithExtras;

const Brands: React.FC = () => {
  const theme = useTheme();
  const [open, setOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<Brand | null>(null);
  const [formData, setFormData] = useState({
    brand_name: '',
    aliases: '',
    is_known_brand: true,
    should_ignore: false,
    category: 'client',
    notes: '',
  });

  const queryClient = useQueryClient();

  const { data: brands, isLoading, error } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.getBrands(),
  });

  const createMutation = useMutation({
    mutationFn: (data: any) => brandsApi.createBrand(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      handleClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      brandsApi.updateBrand(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
      handleClose();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => brandsApi.deleteBrand(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['brands'] });
    },
  });

  const handleOpen = (brand?: Brand) => {
    if (brand) {
      setEditingBrand(brand);
      setFormData({
        brand_name: brand.brand_name,
        aliases: brand.aliases?.join(', ') || '',
        is_known_brand: brand.is_known_brand,
        should_ignore: brand.should_ignore || false,
        category: brand.category || 'client',
        notes: brand.notes || '',
      });
    } else {
      setEditingBrand(null);
      setFormData({
        brand_name: '',
        aliases: '',
        is_known_brand: true,
        should_ignore: false,
        category: 'client',
        notes: '',
      });
    }
    setOpen(true);
  };

  const handleClose = () => {
    setOpen(false);
    setEditingBrand(null);
  };

  const handleSubmit = () => {
    const submitData = {
      brand_name: formData.brand_name,
      aliases: formData.aliases ? formData.aliases.split(',').map(a => a.trim()) : [],
      is_known_brand: formData.is_known_brand,
      should_ignore: formData.should_ignore,
      category: formData.category,
      notes: formData.notes,
    };

    if (editingBrand) {
      updateMutation.mutate({ id: editingBrand.id, data: submitData });
    } else {
      createMutation.mutate(submitData);
    }
  };

  const handleDelete = (id: string) => {
    if (window.confirm('Are you sure you want to delete this brand?')) {
      deleteMutation.mutate(id);
    }
  };

  const getCategoryColor = (category?: string) => {
    switch (category) {
      case 'client':
        return theme.palette.primary.main;
      case 'competitor':
        return theme.palette.error.main;
      case 'partner':
        return theme.palette.success.main;
      default:
        return theme.palette.text.secondary;
    }
  };

  const getStatusIcon = (brand: Brand) => {
    if (brand.should_ignore) return <IgnoredIcon />;
    if (brand.is_known_brand) return <KnownIcon />;
    return <UnknownIcon />;
  };

  const getStatusColor = (brand: Brand) => {
    if (brand.should_ignore) return 'default';
    if (brand.is_known_brand) return 'success';
    return 'warning';
  };

  const getStatusLabel = (brand: Brand) => {
    if (brand.should_ignore) return 'Ignored';
    if (brand.is_known_brand) return 'Known';
    return 'Unknown';
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return <Alert severity="error">Failed to load brands. Please try again later.</Alert>;
  }

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.secondary.light, 0.1)}, ${alpha(theme.palette.info.light, 0.1)})`,
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
            Brands
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Manage your tracked brands, aliases, and categories
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
          Add Brand
        </Button>
      </MotionBox>

      {/* Brands Grid */}
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {brands?.map((brand: Brand, index: number) => (
          <MotionCard
            key={brand.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: index * 0.05 }}
            sx={{
              '&:hover': {
                transform: 'translateX(4px)',
                boxShadow: `0 8px 24px ${alpha(getCategoryColor(brand.category), 0.15)}`,
              },
              transition: 'all 0.3s ease',
              borderLeft: `4px solid ${getCategoryColor(brand.category)}`,
            }}
          >
            <CardContent sx={{ p: 3 }}>
              <Box display="flex" alignItems="flex-start" justifyContent="space-between">
                <Box display="flex" gap={2} flex={1}>
                  <Avatar
                    sx={{
                      width: 56,
                      height: 56,
                      background: `linear-gradient(135deg, ${getCategoryColor(brand.category)}, ${alpha(getCategoryColor(brand.category), 0.7)})`,
                      fontSize: '1.5rem',
                      fontWeight: 600,
                    }}
                  >
                    <BusinessIcon sx={{ fontSize: 28 }} />
                  </Avatar>

                  <Box flex={1}>
                    <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                      <Typography variant="h6" sx={{ fontWeight: 600 }}>
                        {brand.brand_name}
                      </Typography>
                      <Chip
                        icon={getStatusIcon(brand)}
                        label={getStatusLabel(brand)}
                        color={getStatusColor(brand)}
                        size="small"
                        sx={{ fontWeight: 500 }}
                      />
                      <Chip
                        label={brand.category || 'other'}
                        size="small"
                        sx={{
                          backgroundColor: alpha(getCategoryColor(brand.category), 0.1),
                          color: getCategoryColor(brand.category),
                          fontWeight: 500,
                          textTransform: 'capitalize',
                        }}
                      />
                    </Box>

                    {brand.aliases && brand.aliases.length > 0 && (
                      <Box mb={1.5}>
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 500 }}>
                          Aliases:
                        </Typography>
                        <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                          {brand.aliases.map((alias, idx) => (
                            <Chip
                              key={idx}
                              label={alias}
                              size="small"
                              variant="outlined"
                              sx={{ mb: 0.5 }}
                            />
                          ))}
                        </Stack>
                      </Box>
                    )}

                    {brand.notes && (
                      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                        {brand.notes}
                      </Typography>
                    )}
                  </Box>
                </Box>

                <Stack direction="row" spacing={1}>
                  <IconButton
                    size="small"
                    onClick={() => handleOpen(brand)}
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
                    onClick={() => handleDelete(brand.id)}
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
        ))}
      </Box>

      {brands?.length === 0 && (
        <Card sx={{ p: 6, textAlign: 'center' }}>
          <BusinessIcon sx={{ fontSize: 64, color: theme.palette.text.secondary, mb: 2 }} />
          <Typography variant="h6" color="text.secondary" gutterBottom>
            No brands yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Add your first brand to start tracking mentions
          </Typography>
          <Button variant="contained" startIcon={<AddIcon />} onClick={() => handleOpen()}>
            Add Brand
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
            {editingBrand ? 'Edit Brand' : 'Add Brand'}
          </Typography>
        </DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <TextField
            fullWidth
            label="Brand Name"
            value={formData.brand_name}
            onChange={(e) => setFormData({ ...formData, brand_name: e.target.value })}
            margin="normal"
            required
          />
          <TextField
            fullWidth
            label="Aliases (comma-separated)"
            value={formData.aliases}
            onChange={(e) => setFormData({ ...formData, aliases: e.target.value })}
            margin="normal"
            helperText="e.g., Nike Inc, Nike Sports"
          />
          <TextField
            fullWidth
            label="Category"
            value={formData.category}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            margin="normal"
            select
            slotProps={{ select: { native: true } }}
          >
            <option value="client">Client</option>
            <option value="competitor">Competitor</option>
            <option value="partner">Partner</option>
            <option value="other">Other</option>
          </TextField>
          <TextField
            fullWidth
            label="Notes"
            value={formData.notes}
            onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
            margin="normal"
            multiline
            rows={3}
          />
          <Box sx={{ mt: 2 }}>
            <FormControlLabel
              control={
                <Switch
                  checked={formData.is_known_brand}
                  onChange={(e) => setFormData({ ...formData, is_known_brand: e.target.checked })}
                />
              }
              label="Known Brand"
            />
            <FormControlLabel
              control={
                <Switch
                  checked={formData.should_ignore}
                  onChange={(e) => setFormData({ ...formData, should_ignore: e.target.checked })}
                />
              }
              label="Ignore in Reports"
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
            disabled={!formData.brand_name || createMutation.isPending || updateMutation.isPending}
          >
            {editingBrand ? 'Update' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Brands;
