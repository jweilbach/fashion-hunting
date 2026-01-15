import React, { useState } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  Avatar,
  alpha,
  useTheme,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  FormControl,
  InputLabel,
  Select,
  Tooltip,
  Snackbar,
} from '@mui/material';
import {
  Add as AddIcon,
  MoreVert as MoreVertIcon,
  PersonOff as PersonOffIcon,
  PersonAdd as PersonAddIcon,
  AdminPanelSettings as AdminIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { usersApi } from '../api/users';
import type { UserResponse, CreateUserRequest } from '../api/users';
import { useAuth } from '../context/AuthContext';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const UserManagement: React.FC = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuth();

  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [roleDialogOpen, setRoleDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserResponse | null>(null);

  // Form state for new user
  const [newEmail, setNewEmail] = useState('');
  const [newFirstName, setNewFirstName] = useState('');
  const [newLastName, setNewLastName] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');

  // Role change state
  const [selectedRole, setSelectedRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuUser, setMenuUser] = useState<UserResponse | null>(null);

  // Feedback
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Fetch users
  const { data: users, isLoading, error: fetchError } = useQuery({
    queryKey: ['users'],
    queryFn: () => usersApi.listUsers(),
  });

  // Create user mutation
  const createUserMutation = useMutation({
    mutationFn: (data: CreateUserRequest) => usersApi.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSnackbar({ open: true, message: 'User created successfully. Default password is Welcome123', severity: 'success' });
      handleCloseAddDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to create user', severity: 'error' });
    },
  });

  // Update role mutation
  const updateRoleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: 'admin' | 'editor' | 'viewer' }) =>
      usersApi.updateUserRole(userId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSnackbar({ open: true, message: 'User role updated successfully', severity: 'success' });
      handleCloseRoleDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to update role', severity: 'error' });
    },
  });

  // Activate user mutation
  const activateUserMutation = useMutation({
    mutationFn: (userId: string) => usersApi.activateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSnackbar({ open: true, message: 'User activated successfully', severity: 'success' });
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to activate user', severity: 'error' });
    },
  });

  // Deactivate user mutation
  const deactivateUserMutation = useMutation({
    mutationFn: (userId: string) => usersApi.deactivateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSnackbar({ open: true, message: 'User deactivated successfully', severity: 'success' });
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to deactivate user', severity: 'error' });
    },
  });

  // Delete user mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => usersApi.deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      setSnackbar({ open: true, message: 'User deleted successfully', severity: 'success' });
      handleCloseDeleteDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to delete user', severity: 'error' });
    },
  });

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin':
        return theme.palette.error.main;
      case 'editor':
        return theme.palette.warning.main;
      case 'viewer':
        return theme.palette.info.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, user: UserResponse) => {
    setAnchorEl(event.currentTarget);
    setMenuUser(user);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setMenuUser(null);
  };

  const handleOpenAddDialog = () => {
    setAddDialogOpen(true);
  };

  const handleCloseAddDialog = () => {
    setAddDialogOpen(false);
    setNewEmail('');
    setNewFirstName('');
    setNewLastName('');
    setNewRole('viewer');
  };

  const handleOpenRoleDialog = (user: UserResponse) => {
    setSelectedUser(user);
    setSelectedRole(user.role);
    setRoleDialogOpen(true);
    handleMenuClose();
  };

  const handleCloseRoleDialog = () => {
    setRoleDialogOpen(false);
    setSelectedUser(null);
    setSelectedRole('viewer');
  };

  const handleOpenDeleteDialog = (user: UserResponse) => {
    setSelectedUser(user);
    setDeleteDialogOpen(true);
    handleMenuClose();
  };

  const handleCloseDeleteDialog = () => {
    setDeleteDialogOpen(false);
    setSelectedUser(null);
  };

  const handleCreateUser = () => {
    if (!newEmail) {
      setSnackbar({ open: true, message: 'Email is required', severity: 'error' });
      return;
    }

    createUserMutation.mutate({
      email: newEmail,
      first_name: newFirstName || undefined,
      last_name: newLastName || undefined,
      role: newRole,
    });
  };

  const handleUpdateRole = () => {
    if (selectedUser) {
      updateRoleMutation.mutate({ userId: selectedUser.id, role: selectedRole });
    }
  };

  const handleToggleActive = (user: UserResponse) => {
    if (user.is_active) {
      deactivateUserMutation.mutate(user.id);
    } else {
      activateUserMutation.mutate(user.id);
    }
    handleMenuClose();
  };

  const handleDeleteUser = () => {
    if (selectedUser) {
      deleteUserMutation.mutate(selectedUser.id);
    }
  };

  const isCurrentUser = (user: UserResponse) => user.id === currentUser?.id;

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (fetchError) {
    return (
      <Alert severity="error">Failed to load users. Please try again later.</Alert>
    );
  }

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.light, 0.1)}, ${alpha(theme.palette.secondary.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>
              User Management
            </Typography>
            <Typography variant="body1" color="text.secondary" mt={1}>
              Manage users in your organization
            </Typography>
          </Box>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenAddDialog}
            sx={{
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            }}
          >
            Add User
          </Button>
        </Box>
      </MotionBox>

      {/* Users Table */}
      <MotionCard
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <CardContent sx={{ p: 0 }}>
          <TableContainer component={Paper} elevation={0}>
            <Table>
              <TableHead>
                <TableRow sx={{ backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                  <TableCell>User</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Login</TableCell>
                  <TableCell>Created</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users?.map((user) => (
                  <TableRow
                    key={user.id}
                    sx={{
                      '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.02) },
                      opacity: user.is_active ? 1 : 0.6,
                    }}
                  >
                    <TableCell>
                      <Box display="flex" alignItems="center" gap={2}>
                        <Avatar
                          sx={{
                            width: 40,
                            height: 40,
                            background: user.is_active
                              ? `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
                              : theme.palette.grey[400],
                          }}
                        >
                          {(user.first_name?.[0] || user.email[0]).toUpperCase()}
                        </Avatar>
                        <Box>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {user.first_name && user.last_name
                              ? `${user.first_name} ${user.last_name}`
                              : user.email}
                            {isCurrentUser(user) && (
                              <Chip
                                label="You"
                                size="small"
                                sx={{ ml: 1, fontSize: '0.7rem', height: 20 }}
                              />
                            )}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {user.email}
                          </Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.role}
                        size="small"
                        sx={{
                          backgroundColor: alpha(getRoleColor(user.role), 0.1),
                          color: getRoleColor(user.role),
                          fontWeight: 600,
                          textTransform: 'capitalize',
                        }}
                      />
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={user.is_active ? 'Active' : 'Inactive'}
                        size="small"
                        color={user.is_active ? 'success' : 'default'}
                        variant={user.is_active ? 'filled' : 'outlined'}
                      />
                    </TableCell>
                    <TableCell>
                      {user.last_login
                        ? new Date(user.last_login).toLocaleDateString('en-US', {
                            month: 'short',
                            day: 'numeric',
                            year: 'numeric',
                          })
                        : 'Never'}
                    </TableCell>
                    <TableCell>
                      {new Date(user.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="Actions">
                        <IconButton
                          onClick={(e) => handleMenuOpen(e, user)}
                          size="small"
                          disabled={isCurrentUser(user)}
                        >
                          <MoreVertIcon />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                ))}
                {(!users || users.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} align="center" sx={{ py: 4 }}>
                      <Typography color="text.secondary">No users found</Typography>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
        </CardContent>
      </MotionCard>

      {/* Actions Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={() => menuUser && handleOpenRoleDialog(menuUser)}>
          <AdminIcon sx={{ mr: 1 }} fontSize="small" />
          Change Role
        </MenuItem>
        <MenuItem onClick={() => menuUser && handleToggleActive(menuUser)}>
          {menuUser?.is_active ? (
            <>
              <PersonOffIcon sx={{ mr: 1 }} fontSize="small" />
              Deactivate
            </>
          ) : (
            <>
              <PersonAddIcon sx={{ mr: 1 }} fontSize="small" />
              Activate
            </>
          )}
        </MenuItem>
        <MenuItem
          onClick={() => menuUser && handleOpenDeleteDialog(menuUser)}
          sx={{ color: theme.palette.error.main }}
        >
          <DeleteIcon sx={{ mr: 1 }} fontSize="small" />
          Delete
        </MenuItem>
      </Menu>

      {/* Add User Dialog */}
      <Dialog open={addDialogOpen} onClose={handleCloseAddDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add New User</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 2 }}>
            <TextField
              label="Email"
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              fullWidth
              required
              autoFocus
            />
            <Stack direction="row" spacing={2}>
              <TextField
                label="First Name"
                value={newFirstName}
                onChange={(e) => setNewFirstName(e.target.value)}
                fullWidth
              />
              <TextField
                label="Last Name"
                value={newLastName}
                onChange={(e) => setNewLastName(e.target.value)}
                fullWidth
              />
            </Stack>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={newRole}
                label="Role"
                onChange={(e) => setNewRole(e.target.value as 'admin' | 'editor' | 'viewer')}
              >
                <MenuItem value="viewer">Viewer</MenuItem>
                <MenuItem value="editor">Editor</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
            <Alert severity="info" sx={{ mt: 1 }}>
              The user will be created with the default password: <strong>Welcome123</strong>
            </Alert>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseAddDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleCreateUser}
            variant="contained"
            disabled={createUserMutation.isPending}
          >
            {createUserMutation.isPending ? 'Creating...' : 'Create User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Change Role Dialog */}
      <Dialog open={roleDialogOpen} onClose={handleCloseRoleDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Change User Role</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Change role for: <strong>{selectedUser?.email}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Role</InputLabel>
              <Select
                value={selectedRole}
                label="Role"
                onChange={(e) => setSelectedRole(e.target.value as 'admin' | 'editor' | 'viewer')}
              >
                <MenuItem value="viewer">Viewer</MenuItem>
                <MenuItem value="editor">Editor</MenuItem>
                <MenuItem value="admin">Admin</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseRoleDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleUpdateRole}
            variant="contained"
            disabled={updateRoleMutation.isPending}
          >
            {updateRoleMutation.isPending ? 'Updating...' : 'Update Role'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={handleCloseDeleteDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete <strong>{selectedUser?.email}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This action cannot be undone. Consider deactivating the user instead.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDeleteDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleDeleteUser}
            variant="contained"
            color="error"
            disabled={deleteUserMutation.isPending}
          >
            {deleteUserMutation.isPending ? 'Deleting...' : 'Delete User'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for feedback */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={5000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default UserManagement;
