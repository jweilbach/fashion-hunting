import React from 'react';
import { Box, Typography, Button, alpha, useTheme } from '@mui/material';
import { ExitToApp as ExitIcon, Warning as WarningIcon } from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

const ImpersonationBanner: React.FC = () => {
  const theme = useTheme();
  const { isImpersonating, impersonatedUser, endImpersonation } = useAuth();

  if (!isImpersonating || !impersonatedUser) {
    return null;
  }

  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: theme.zIndex.appBar + 100,
        background: `linear-gradient(90deg, ${theme.palette.warning.dark}, ${theme.palette.warning.main})`,
        color: theme.palette.warning.contrastText,
        py: 1,
        px: 2,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        boxShadow: `0 2px 8px ${alpha(theme.palette.warning.dark, 0.3)}`,
      }}
    >
      <WarningIcon fontSize="small" />
      <Typography variant="body2" sx={{ fontWeight: 500 }}>
        You are impersonating{' '}
        <strong>
          {impersonatedUser.full_name || impersonatedUser.email}
        </strong>
        {impersonatedUser.full_name && (
          <span style={{ opacity: 0.8 }}> ({impersonatedUser.email})</span>
        )}
      </Typography>
      <Button
        variant="contained"
        size="small"
        startIcon={<ExitIcon />}
        onClick={endImpersonation}
        sx={{
          ml: 2,
          backgroundColor: alpha(theme.palette.common.white, 0.2),
          color: theme.palette.warning.contrastText,
          '&:hover': {
            backgroundColor: alpha(theme.palette.common.white, 0.3),
          },
        }}
      >
        End Impersonation
      </Button>
    </Box>
  );
};

export default ImpersonationBanner;
