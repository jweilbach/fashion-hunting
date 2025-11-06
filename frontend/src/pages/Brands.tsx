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
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { brandsApi } from '../api/brands';

interface Brand {
  id: string;
  brand_name: string;
  aliases?: string[];
  is_known_brand: boolean;
  should_ignore: boolean;
  category?: string;
  notes?: string;
}

const Brands: React.FC = () => {
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
        should_ignore: brand.should_ignore,
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
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h3">Brands</Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => handleOpen()}
        >
          Add Brand
        </Button>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Brand Name</TableCell>
              <TableCell>Aliases</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {brands?.map((brand: Brand) => (
              <TableRow key={brand.id}>
                <TableCell>{brand.brand_name}</TableCell>
                <TableCell>
                  {brand.aliases?.map((alias, idx) => (
                    <Chip key={idx} label={alias} size="small" sx={{ mr: 0.5 }} />
                  ))}
                </TableCell>
                <TableCell>{brand.category}</TableCell>
                <TableCell>
                  {brand.should_ignore ? (
                    <Chip label="Ignored" color="default" size="small" />
                  ) : brand.is_known_brand ? (
                    <Chip label="Known" color="success" size="small" />
                  ) : (
                    <Chip label="Unknown" color="warning" size="small" />
                  )}
                </TableCell>
                <TableCell align="right">
                  <IconButton
                    size="small"
                    onClick={() => handleOpen(brand)}
                    color="primary"
                  >
                    <EditIcon />
                  </IconButton>
                  <IconButton
                    size="small"
                    onClick={() => handleDelete(brand.id)}
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
        <DialogTitle>{editingBrand ? 'Edit Brand' : 'Add Brand'}</DialogTitle>
        <DialogContent>
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
            SelectProps={{ native: true }}
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
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose}>Cancel</Button>
          <Button
            onClick={handleSubmit}
            variant="contained"
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
