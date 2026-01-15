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
  Grid,
  InputAdornment,
  Pagination,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  MoreVert as MoreVertIcon,
  Business as BusinessIcon,
  Block as BlockIcon,
  CheckCircle as CheckCircleIcon,
  SwapHoriz as SwapHorizIcon,
  TrendingUp as TrendingUpIcon,
  People as PeopleIcon,
  Description as DescriptionIcon,
  PersonSearch as PersonSearchIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { adminApi } from '../api/admin';
import type {
  TenantAdminResponse,
  TenantListParams,
  AdminUserSearchResult,
} from '../api/admin';
import { useAuth } from '../context/AuthContext';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
}

const AdminDashboard: React.FC = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();
  const { startImpersonation } = useAuth();

  // Tab state
  const [activeTab, setActiveTab] = useState(0);

  // Tenant list state
  const [tenantParams, setTenantParams] = useState<TenantListParams>({
    page: 1,
    page_size: 10,
  });
  const [searchTerm, setSearchTerm] = useState('');

  // User search state
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [userSearchResults, setUserSearchResults] = useState<AdminUserSearchResult[]>([]);
  const [isSearchingUsers, setIsSearchingUsers] = useState(false);

  // Dialog states
  const [statusDialogOpen, setStatusDialogOpen] = useState(false);
  const [planDialogOpen, setPlanDialogOpen] = useState(false);
  const [impersonateDialogOpen, setImpersonateDialogOpen] = useState(false);
  const [selectedTenant, setSelectedTenant] = useState<TenantAdminResponse | null>(null);
  const [selectedUser, setSelectedUser] = useState<AdminUserSearchResult | null>(null);

  // Form state
  const [newStatus, setNewStatus] = useState<'active' | 'suspended' | 'cancelled'>('active');
  const [newPlan, setNewPlan] = useState<'free' | 'starter' | 'professional' | 'enterprise'>('free');

  // Menu state
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [menuTenant, setMenuTenant] = useState<TenantAdminResponse | null>(null);

  // Feedback
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  });

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: () => adminApi.getStats(),
  });

  // Fetch tenants
  const { data: tenantsData, isLoading: isLoadingTenants, error: tenantsError } = useQuery({
    queryKey: ['admin-tenants', tenantParams],
    queryFn: () => adminApi.listTenants(tenantParams),
  });

  // Update status mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ tenantId, status }: { tenantId: string; status: 'active' | 'suspended' | 'cancelled' }) =>
      adminApi.updateTenantStatus(tenantId, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      setSnackbar({ open: true, message: 'Tenant status updated successfully', severity: 'success' });
      handleCloseStatusDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to update status', severity: 'error' });
    },
  });

  // Update plan mutation
  const updatePlanMutation = useMutation({
    mutationFn: ({ tenantId, plan }: { tenantId: string; plan: 'free' | 'starter' | 'professional' | 'enterprise' }) =>
      adminApi.updateTenantPlan(tenantId, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-tenants'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      setSnackbar({ open: true, message: 'Tenant plan updated successfully', severity: 'success' });
      handleClosePlanDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to update plan', severity: 'error' });
    },
  });

  // Impersonate mutation
  const impersonateMutation = useMutation({
    mutationFn: (userId: string) => adminApi.impersonateUser(userId),
    onSuccess: (data) => {
      startImpersonation(data.access_token, data.impersonated_user, data.impersonated_by);
      setSnackbar({ open: true, message: `Now impersonating ${data.impersonated_user.email}`, severity: 'success' });
      handleCloseImpersonateDialog();
    },
    onError: (err: Error) => {
      setSnackbar({ open: true, message: err.message || 'Failed to impersonate user', severity: 'error' });
    },
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return theme.palette.success.main;
      case 'suspended':
        return theme.palette.warning.main;
      case 'cancelled':
        return theme.palette.error.main;
      default:
        return theme.palette.grey[500];
    }
  };

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return theme.palette.primary.main;
      case 'professional':
        return theme.palette.secondary.main;
      case 'starter':
        return theme.palette.info.main;
      case 'free':
        return theme.palette.grey[500];
      default:
        return theme.palette.grey[500];
    }
  };

  const handleSearch = () => {
    setTenantParams((prev) => ({ ...prev, search: searchTerm, page: 1 }));
  };

  const handleUserSearch = async () => {
    if (userSearchQuery.length < 2) {
      setSnackbar({ open: true, message: 'Search query must be at least 2 characters', severity: 'error' });
      return;
    }
    setIsSearchingUsers(true);
    try {
      const results = await adminApi.searchUsers(userSearchQuery, 20);
      setUserSearchResults(results);
    } catch (err) {
      setSnackbar({ open: true, message: 'Failed to search users', severity: 'error' });
    } finally {
      setIsSearchingUsers(false);
    }
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, tenant: TenantAdminResponse) => {
    setAnchorEl(event.currentTarget);
    setMenuTenant(tenant);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setMenuTenant(null);
  };

  const handleOpenStatusDialog = (tenant: TenantAdminResponse) => {
    setSelectedTenant(tenant);
    setNewStatus(tenant.status);
    setStatusDialogOpen(true);
    handleMenuClose();
  };

  const handleCloseStatusDialog = () => {
    setStatusDialogOpen(false);
    setSelectedTenant(null);
  };

  const handleOpenPlanDialog = (tenant: TenantAdminResponse) => {
    setSelectedTenant(tenant);
    setNewPlan(tenant.plan);
    setPlanDialogOpen(true);
    handleMenuClose();
  };

  const handleClosePlanDialog = () => {
    setPlanDialogOpen(false);
    setSelectedTenant(null);
  };

  const handleOpenImpersonateDialog = (user: AdminUserSearchResult) => {
    setSelectedUser(user);
    setImpersonateDialogOpen(true);
  };

  const handleCloseImpersonateDialog = () => {
    setImpersonateDialogOpen(false);
    setSelectedUser(null);
  };

  const handleUpdateStatus = () => {
    if (selectedTenant) {
      updateStatusMutation.mutate({ tenantId: selectedTenant.id, status: newStatus });
    }
  };

  const handleUpdatePlan = () => {
    if (selectedTenant) {
      updatePlanMutation.mutate({ tenantId: selectedTenant.id, plan: newPlan });
    }
  };

  const handleImpersonate = () => {
    if (selectedUser) {
      impersonateMutation.mutate(selectedUser.id);
    }
  };

  return (
    <Box>
      {/* Header */}
      <MotionBox
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        sx={{
          background: `linear-gradient(135deg, ${alpha(theme.palette.error.light, 0.1)}, ${alpha(theme.palette.warning.light, 0.1)})`,
          borderRadius: 3,
          p: 4,
          mb: 4,
        }}
      >
        <Typography variant="h4" sx={{ fontWeight: 600 }}>
          Super Admin Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary" mt={1}>
          Cross-tenant management and system administration
        </Typography>
      </MotionBox>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <MotionCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    background: alpha(theme.palette.primary.main, 0.1),
                  }}
                >
                  <BusinessIcon sx={{ color: theme.palette.primary.main }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {stats?.tenants.total || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Tenants
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </MotionCard>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MotionCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    background: alpha(theme.palette.success.main, 0.1),
                  }}
                >
                  <CheckCircleIcon sx={{ color: theme.palette.success.main }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {stats?.tenants.active || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Active Tenants
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </MotionCard>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MotionCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    background: alpha(theme.palette.info.main, 0.1),
                  }}
                >
                  <PeopleIcon sx={{ color: theme.palette.info.main }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {stats?.users.total || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Users
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </MotionCard>
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <MotionCard
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <CardContent>
              <Box display="flex" alignItems="center" gap={2}>
                <Box
                  sx={{
                    p: 1.5,
                    borderRadius: 2,
                    background: alpha(theme.palette.secondary.main, 0.1),
                  }}
                >
                  <DescriptionIcon sx={{ color: theme.palette.secondary.main }} />
                </Box>
                <Box>
                  <Typography variant="h4" sx={{ fontWeight: 700 }}>
                    {stats?.reports.total || 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total Reports
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </MotionCard>
        </Grid>
      </Grid>

      {/* Tabs */}
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)}>
          <Tab label="Tenants" icon={<BusinessIcon />} iconPosition="start" />
          <Tab label="User Search" icon={<PersonSearchIcon />} iconPosition="start" />
        </Tabs>
      </Box>

      {/* Tenants Tab */}
      <TabPanel value={activeTab} index={0}>
        {/* Search and Filters */}
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              placeholder="Search tenants..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              size="small"
              sx={{ width: 300 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Status</InputLabel>
              <Select
                value={tenantParams.status_filter || ''}
                label="Status"
                onChange={(e) =>
                  setTenantParams((prev) => ({
                    ...prev,
                    status_filter: e.target.value as TenantListParams['status_filter'] || undefined,
                    page: 1,
                  }))
                }
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="suspended">Suspended</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 120 }}>
              <InputLabel>Plan</InputLabel>
              <Select
                value={tenantParams.plan_filter || ''}
                label="Plan"
                onChange={(e) =>
                  setTenantParams((prev) => ({
                    ...prev,
                    plan_filter: e.target.value as TenantListParams['plan_filter'] || undefined,
                    page: 1,
                  }))
                }
              >
                <MenuItem value="">All</MenuItem>
                <MenuItem value="free">Free</MenuItem>
                <MenuItem value="starter">Starter</MenuItem>
                <MenuItem value="professional">Professional</MenuItem>
                <MenuItem value="enterprise">Enterprise</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" onClick={handleSearch}>
              Search
            </Button>
          </Stack>
        </Box>

        {/* Tenants Table */}
        {isLoadingTenants ? (
          <Box display="flex" justifyContent="center" py={4}>
            <CircularProgress />
          </Box>
        ) : tenantsError ? (
          <Alert severity="error">Failed to load tenants. Please try again.</Alert>
        ) : (
          <>
            <TableContainer component={Paper}>
              <Table>
                <TableHead>
                  <TableRow sx={{ backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                    <TableCell>Tenant</TableCell>
                    <TableCell>Plan</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell align="right">Users</TableCell>
                    <TableCell align="right">Reports</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {tenantsData?.items.map((tenant) => (
                    <TableRow
                      key={tenant.id}
                      sx={{
                        '&:hover': { backgroundColor: alpha(theme.palette.primary.main, 0.02) },
                        opacity: tenant.status === 'active' ? 1 : 0.6,
                      }}
                    >
                      <TableCell>
                        <Box>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {tenant.name}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            {tenant.email}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={tenant.plan}
                          size="small"
                          sx={{
                            backgroundColor: alpha(getPlanColor(tenant.plan), 0.1),
                            color: getPlanColor(tenant.plan),
                            fontWeight: 600,
                            textTransform: 'capitalize',
                          }}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={tenant.status}
                          size="small"
                          sx={{
                            backgroundColor: alpha(getStatusColor(tenant.status), 0.1),
                            color: getStatusColor(tenant.status),
                            fontWeight: 600,
                            textTransform: 'capitalize',
                          }}
                        />
                      </TableCell>
                      <TableCell align="right">{tenant.user_count}</TableCell>
                      <TableCell align="right">{tenant.report_count}</TableCell>
                      <TableCell>
                        {new Date(tenant.created_at).toLocaleDateString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          year: 'numeric',
                        })}
                      </TableCell>
                      <TableCell align="right">
                        <Tooltip title="Actions">
                          <IconButton onClick={(e) => handleMenuOpen(e, tenant)} size="small">
                            <MoreVertIcon />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            {/* Pagination */}
            {tenantsData && tenantsData.pages > 1 && (
              <Box display="flex" justifyContent="center" mt={3}>
                <Pagination
                  count={tenantsData.pages}
                  page={tenantParams.page || 1}
                  onChange={(_, page) => setTenantParams((prev) => ({ ...prev, page }))}
                  color="primary"
                />
              </Box>
            )}
          </>
        )}
      </TabPanel>

      {/* User Search Tab */}
      <TabPanel value={activeTab} index={1}>
        <Box sx={{ mb: 3 }}>
          <Stack direction="row" spacing={2} alignItems="center">
            <TextField
              placeholder="Search by email or name..."
              value={userSearchQuery}
              onChange={(e) => setUserSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleUserSearch()}
              size="small"
              sx={{ width: 400 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon />
                  </InputAdornment>
                ),
              }}
            />
            <Button
              variant="contained"
              onClick={handleUserSearch}
              disabled={isSearchingUsers}
            >
              {isSearchingUsers ? 'Searching...' : 'Search Users'}
            </Button>
          </Stack>
        </Box>

        {userSearchResults.length > 0 ? (
          <Paper>
            <List>
              {userSearchResults.map((user, index) => (
                <React.Fragment key={user.id}>
                  {index > 0 && <Divider />}
                  <ListItem
                    secondaryAction={
                      !user.is_superuser && (
                        <Tooltip title="Impersonate this user">
                          <IconButton
                            edge="end"
                            onClick={() => handleOpenImpersonateDialog(user)}
                          >
                            <SwapHorizIcon />
                          </IconButton>
                        </Tooltip>
                      )
                    }
                  >
                    <ListItemAvatar>
                      <Avatar
                        sx={{
                          background: user.is_active
                            ? `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`
                            : theme.palette.grey[400],
                        }}
                      >
                        {(user.first_name?.[0] || user.email[0]).toUpperCase()}
                      </Avatar>
                    </ListItemAvatar>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1" sx={{ fontWeight: 500 }}>
                            {user.full_name || user.email}
                          </Typography>
                          {user.is_superuser && (
                            <Chip label="Superuser" size="small" color="error" />
                          )}
                          {!user.is_active && (
                            <Chip label="Inactive" size="small" variant="outlined" />
                          )}
                        </Box>
                      }
                      secondary={
                        <Typography variant="body2" color="text.secondary">
                          {user.email} &bull; {user.tenant_name} &bull; {user.role}
                        </Typography>
                      }
                    />
                  </ListItem>
                </React.Fragment>
              ))}
            </List>
          </Paper>
        ) : (
          <Typography color="text.secondary" textAlign="center" py={4}>
            Search for users across all tenants by email or name
          </Typography>
        )}
      </TabPanel>

      {/* Actions Menu */}
      <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleMenuClose}>
        <MenuItem onClick={() => menuTenant && handleOpenStatusDialog(menuTenant)}>
          {menuTenant?.status === 'active' ? (
            <>
              <BlockIcon sx={{ mr: 1 }} fontSize="small" />
              Suspend Tenant
            </>
          ) : (
            <>
              <CheckCircleIcon sx={{ mr: 1 }} fontSize="small" />
              Activate Tenant
            </>
          )}
        </MenuItem>
        <MenuItem onClick={() => menuTenant && handleOpenPlanDialog(menuTenant)}>
          <TrendingUpIcon sx={{ mr: 1 }} fontSize="small" />
          Change Plan
        </MenuItem>
      </Menu>

      {/* Update Status Dialog */}
      <Dialog open={statusDialogOpen} onClose={handleCloseStatusDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Update Tenant Status</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Change status for: <strong>{selectedTenant?.name}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Status</InputLabel>
              <Select
                value={newStatus}
                label="Status"
                onChange={(e) => setNewStatus(e.target.value as 'active' | 'suspended' | 'cancelled')}
              >
                <MenuItem value="active">Active</MenuItem>
                <MenuItem value="suspended">Suspended</MenuItem>
                <MenuItem value="cancelled">Cancelled</MenuItem>
              </Select>
            </FormControl>
            {newStatus === 'suspended' && (
              <Alert severity="warning">
                Suspended tenants will not be able to access the platform until reactivated.
              </Alert>
            )}
            {newStatus === 'cancelled' && (
              <Alert severity="error">
                Cancelled tenants will lose access permanently. This should only be used for terminated accounts.
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseStatusDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleUpdateStatus}
            variant="contained"
            disabled={updateStatusMutation.isPending}
          >
            {updateStatusMutation.isPending ? 'Updating...' : 'Update Status'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Update Plan Dialog */}
      <Dialog open={planDialogOpen} onClose={handleClosePlanDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Change Subscription Plan</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ mt: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Change plan for: <strong>{selectedTenant?.name}</strong>
            </Typography>
            <FormControl fullWidth>
              <InputLabel>Plan</InputLabel>
              <Select
                value={newPlan}
                label="Plan"
                onChange={(e) =>
                  setNewPlan(e.target.value as 'free' | 'starter' | 'professional' | 'enterprise')
                }
              >
                <MenuItem value="free">Free</MenuItem>
                <MenuItem value="starter">Starter</MenuItem>
                <MenuItem value="professional">Professional</MenuItem>
                <MenuItem value="enterprise">Enterprise</MenuItem>
              </Select>
            </FormControl>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClosePlanDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleUpdatePlan}
            variant="contained"
            disabled={updatePlanMutation.isPending}
          >
            {updatePlanMutation.isPending ? 'Updating...' : 'Update Plan'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Impersonate Confirmation Dialog */}
      <Dialog open={impersonateDialogOpen} onClose={handleCloseImpersonateDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Impersonate User</DialogTitle>
        <DialogContent>
          <Alert severity="warning" sx={{ mb: 2 }}>
            You are about to impersonate another user. All actions will be logged with your super admin identity.
          </Alert>
          <Typography>
            Are you sure you want to impersonate <strong>{selectedUser?.email}</strong> from{' '}
            <strong>{selectedUser?.tenant_name}</strong>?
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            The impersonation session will expire in 1 hour.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseImpersonateDialog} color="inherit">
            Cancel
          </Button>
          <Button
            onClick={handleImpersonate}
            variant="contained"
            color="warning"
            disabled={impersonateMutation.isPending}
          >
            {impersonateMutation.isPending ? 'Starting...' : 'Start Impersonation'}
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

export default AdminDashboard;
