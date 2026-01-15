import React, { useState, useEffect } from 'react';
import {
  Typography,
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  Stack,
  Avatar,
  alpha,
  useTheme,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  Person as PersonIcon,
  Business as BusinessIcon,
  Lock as LockIcon,
  Visibility,
  VisibilityOff,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { profileApi } from '../api/profile';
import type { ProfileUpdate } from '../api/profile';

const MotionCard = motion.create(Card);
const MotionBox = motion.create(Box);

const Profile: React.FC = () => {
  const theme = useTheme();
  const queryClient = useQueryClient();

  // Profile editing state
  const [isEditing, setIsEditing] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  // Password change state
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  // Feedback state
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');

  // Fetch profile
  const { data: profile, isLoading, error: fetchError } = useQuery({
    queryKey: ['profile'],
    queryFn: () => profileApi.getProfile(),
  });

  // Update form when profile loads
  useEffect(() => {
    if (profile) {
      setFirstName(profile.first_name || '');
      setLastName(profile.last_name || '');
    }
  }, [profile]);

  // Update profile mutation
  const updateProfileMutation = useMutation({
    mutationFn: (data: ProfileUpdate) => profileApi.updateProfile(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      setSuccess('Profile updated successfully');
      setIsEditing(false);
      setTimeout(() => setSuccess(''), 3000);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to update profile');
      setTimeout(() => setError(''), 5000);
    },
  });

  // Change password mutation
  const changePasswordMutation = useMutation({
    mutationFn: (data: { current_password: string; new_password: string }) =>
      profileApi.changePassword(data),
    onSuccess: () => {
      setSuccess('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setShowPasswordSection(false);
      setTimeout(() => setSuccess(''), 3000);
    },
    onError: (err: Error) => {
      setError(err.message || 'Failed to change password');
      setTimeout(() => setError(''), 5000);
    },
  });

  const handleSaveProfile = () => {
    updateProfileMutation.mutate({
      first_name: firstName,
      last_name: lastName,
    });
  };

  const handleCancelEdit = () => {
    setFirstName(profile?.first_name || '');
    setLastName(profile?.last_name || '');
    setIsEditing(false);
  };

  const handleChangePassword = () => {
    setError('');

    if (!currentPassword) {
      setError('Current password is required');
      return;
    }
    if (!newPassword) {
      setError('New password is required');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match');
      return;
    }

    changePasswordMutation.mutate({
      current_password: currentPassword,
      new_password: newPassword,
    });
  };

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

  const getPlanColor = (plan: string | null) => {
    switch (plan) {
      case 'enterprise':
        return theme.palette.error.main;
      case 'professional':
        return theme.palette.warning.main;
      case 'starter':
        return theme.palette.info.main;
      case 'free':
      default:
        return theme.palette.grey[500];
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
      </Box>
    );
  }

  if (fetchError || !profile) {
    return (
      <Alert severity="error">Failed to load profile. Please try again later.</Alert>
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
        <Box display="flex" alignItems="center" gap={3}>
          <Avatar
            sx={{
              width: 80,
              height: 80,
              fontSize: '2rem',
              background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.secondary.main})`,
            }}
          >
            {(profile.first_name?.[0] || profile.email[0]).toUpperCase()}
          </Avatar>
          <Box>
            <Typography variant="h4" sx={{ fontWeight: 600 }}>
              {profile.first_name && profile.last_name
                ? `${profile.first_name} ${profile.last_name}`
                : profile.email}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {profile.email}
            </Typography>
            <Stack direction="row" spacing={1} mt={1}>
              <Chip
                label={profile.role}
                size="small"
                sx={{
                  backgroundColor: alpha(getRoleColor(profile.role), 0.1),
                  color: getRoleColor(profile.role),
                  fontWeight: 600,
                  textTransform: 'capitalize',
                }}
              />
              {profile.tenant_plan && (
                <Chip
                  label={`${profile.tenant_plan} plan`}
                  size="small"
                  sx={{
                    backgroundColor: alpha(getPlanColor(profile.tenant_plan), 0.1),
                    color: getPlanColor(profile.tenant_plan),
                    fontWeight: 500,
                    textTransform: 'capitalize',
                  }}
                />
              )}
            </Stack>
          </Box>
        </Box>
      </MotionBox>

      {/* Alerts */}
      {success && (
        <Alert severity="success" sx={{ mb: 3 }}>
          {success}
        </Alert>
      )}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Stack spacing={3}>
        {/* Profile Information Card */}
        <MotionCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <PersonIcon sx={{ color: theme.palette.primary.main }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Profile Information
                </Typography>
              </Box>
              {!isEditing ? (
                <Button
                  startIcon={<EditIcon />}
                  onClick={() => setIsEditing(true)}
                  variant="outlined"
                  size="small"
                >
                  Edit
                </Button>
              ) : (
                <Stack direction="row" spacing={1}>
                  <Button
                    startIcon={<CancelIcon />}
                    onClick={handleCancelEdit}
                    variant="outlined"
                    size="small"
                    color="inherit"
                  >
                    Cancel
                  </Button>
                  <Button
                    startIcon={<SaveIcon />}
                    onClick={handleSaveProfile}
                    variant="contained"
                    size="small"
                    disabled={updateProfileMutation.isPending}
                  >
                    {updateProfileMutation.isPending ? 'Saving...' : 'Save'}
                  </Button>
                </Stack>
              )}
            </Box>

            <Stack spacing={2}>
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
                <TextField
                  label="First Name"
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  disabled={!isEditing}
                  fullWidth
                />
                <TextField
                  label="Last Name"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  disabled={!isEditing}
                  fullWidth
                />
              </Stack>
              <TextField
                label="Email"
                value={profile.email}
                disabled
                fullWidth
                helperText="Email cannot be changed"
              />
            </Stack>
          </CardContent>
        </MotionCard>

        {/* Organization Card */}
        <MotionCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" gap={1} mb={3}>
              <BusinessIcon sx={{ color: theme.palette.info.main }} />
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Organization
              </Typography>
            </Box>

            <Stack spacing={2}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Organization Name
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {profile.tenant_name || 'Not set'}
                </Typography>
              </Box>
              <Divider />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Subscription Plan
                </Typography>
                <Chip
                  label={profile.tenant_plan || 'free'}
                  size="small"
                  sx={{
                    mt: 0.5,
                    backgroundColor: alpha(getPlanColor(profile.tenant_plan), 0.1),
                    color: getPlanColor(profile.tenant_plan),
                    fontWeight: 500,
                    textTransform: 'capitalize',
                  }}
                />
              </Box>
              <Divider />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Your Role
                </Typography>
                <Chip
                  label={profile.role}
                  size="small"
                  sx={{
                    mt: 0.5,
                    backgroundColor: alpha(getRoleColor(profile.role), 0.1),
                    color: getRoleColor(profile.role),
                    fontWeight: 600,
                    textTransform: 'capitalize',
                  }}
                />
              </Box>
              <Divider />
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Member Since
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 500 }}>
                  {new Date(profile.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </MotionCard>

        {/* Change Password Card */}
        <MotionCard
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <CardContent sx={{ p: 3 }}>
            <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
              <Box display="flex" alignItems="center" gap={1}>
                <LockIcon sx={{ color: theme.palette.warning.main }} />
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  Security
                </Typography>
              </Box>
              {!showPasswordSection && (
                <Button
                  onClick={() => setShowPasswordSection(true)}
                  variant="outlined"
                  size="small"
                >
                  Change Password
                </Button>
              )}
            </Box>

            {showPasswordSection ? (
              <Stack spacing={2}>
                <TextField
                  label="Current Password"
                  type={showCurrentPassword ? 'text' : 'password'}
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  fullWidth
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                          edge="end"
                        >
                          {showCurrentPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  label="New Password"
                  type={showNewPassword ? 'text' : 'password'}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  fullWidth
                  helperText="Must be at least 8 characters"
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowNewPassword(!showNewPassword)}
                          edge="end"
                        >
                          {showNewPassword ? <VisibilityOff /> : <Visibility />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
                <TextField
                  label="Confirm New Password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  fullWidth
                  error={confirmPassword !== '' && confirmPassword !== newPassword}
                  helperText={
                    confirmPassword !== '' && confirmPassword !== newPassword
                      ? 'Passwords do not match'
                      : ''
                  }
                />
                <Stack direction="row" spacing={2} justifyContent="flex-end">
                  <Button
                    onClick={() => {
                      setShowPasswordSection(false);
                      setCurrentPassword('');
                      setNewPassword('');
                      setConfirmPassword('');
                    }}
                    variant="outlined"
                    color="inherit"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleChangePassword}
                    variant="contained"
                    disabled={changePasswordMutation.isPending}
                  >
                    {changePasswordMutation.isPending ? 'Changing...' : 'Change Password'}
                  </Button>
                </Stack>
              </Stack>
            ) : (
              <Typography variant="body2" color="text.secondary">
                Keep your account secure by using a strong password.
              </Typography>
            )}
          </CardContent>
        </MotionCard>
      </Stack>
    </Box>
  );
};

export default Profile;
