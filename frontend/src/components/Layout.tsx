import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  Button,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Avatar,
  alpha,
  useTheme,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  RssFeed as FeedsIcon,
  Business as BrandIcon,
  WorkOutline as JobsIcon,
  Assessment as ReportsIcon,
  LogoutOutlined as LogoutIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';

const drawerWidth = 260;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Brands', icon: <BrandIcon />, path: '/brands' },
    { text: 'Feeds', icon: <FeedsIcon />, path: '/feeds' },
    { text: 'Jobs', icon: <JobsIcon />, path: '/jobs' },
    { text: 'Reports', icon: <ReportsIcon />, path: '/reports' },
  ];

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          zIndex: (theme) => theme.zIndex.drawer + 1,
          background: `linear-gradient(135deg, ${theme.palette.primary.light}, ${theme.palette.secondary.light})`,
          backdropFilter: 'blur(10px)',
        }}
      >
        <Toolbar>
          <Box sx={{ flexGrow: 1 }}>
            <Typography
              variant="h6"
              component="div"
              sx={{
                fontFamily: "'Playfair Display', serif",
                fontWeight: 600,
                letterSpacing: '0.5px',
                lineHeight: 1.2,
              }}
            >
              Marketing Hunting
            </Typography>
            <Typography
              variant="caption"
              component="div"
              sx={{
                fontFamily: "'Playfair Display', serif",
                fontWeight: 400,
                opacity: 0.85,
                fontSize: '0.7rem',
              }}
            >
              A Lavacake Product
            </Typography>
          </Box>
          {user && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ textAlign: 'right', display: { xs: 'none', sm: 'block' } }}>
                <Typography variant="body2" sx={{ fontWeight: 500 }}>
                  {user.email}
                </Typography>
                {user.tenant_name && (
                  <Typography variant="caption" sx={{ opacity: 0.9 }}>
                    {user.tenant_name}
                  </Typography>
                )}
              </Box>
              <Avatar
                sx={{
                  width: 40,
                  height: 40,
                  background: `linear-gradient(135deg, ${theme.palette.secondary.main}, ${theme.palette.secondary.dark})`,
                  fontWeight: 600,
                  fontSize: '1rem',
                }}
              >
                {user.email.charAt(0).toUpperCase()}
              </Avatar>
              <Button
                color="inherit"
                onClick={handleLogout}
                startIcon={<LogoutIcon />}
                sx={{
                  textTransform: 'none',
                  fontWeight: 500,
                  px: 2,
                  '&:hover': {
                    backgroundColor: alpha(theme.palette.common.white, 0.1),
                  },
                }}
              >
                Logout
              </Button>
            </Box>
          )}
        </Toolbar>
      </AppBar>

      {/* Sidebar */}
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: 'none',
            background: `linear-gradient(180deg, ${alpha(theme.palette.primary.light, 0.05)}, ${alpha(theme.palette.secondary.light, 0.05)})`,
          },
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        <Box sx={{ overflow: 'auto', p: 2 }}>
          <List sx={{ p: 0 }}>
            {menuItems.map((item) => {
              const isSelected = location.pathname === item.path;
              return (
                <ListItem key={item.text} disablePadding sx={{ mb: 0.5 }}>
                  <ListItemButton
                    selected={isSelected}
                    onClick={() => navigate(item.path)}
                    sx={{
                      borderRadius: 2,
                      transition: 'all 0.3s ease',
                      ...(isSelected && {
                        background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.15)}, ${alpha(theme.palette.secondary.main, 0.15)})`,
                        boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.2)}`,
                        '&:hover': {
                          background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.2)}, ${alpha(theme.palette.secondary.main, 0.2)})`,
                        },
                      }),
                      ...(!isSelected && {
                        '&:hover': {
                          background: alpha(theme.palette.primary.main, 0.08),
                          transform: 'translateX(4px)',
                        },
                      }),
                    }}
                  >
                    <ListItemIcon
                      sx={{
                        minWidth: 40,
                        color: isSelected ? theme.palette.primary.main : theme.palette.text.secondary,
                      }}
                    >
                      {item.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={item.text}
                      primaryTypographyProps={{
                        fontWeight: isSelected ? 600 : 500,
                        fontSize: '0.95rem',
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}
          </List>

          {/* Sidebar Footer */}
          <Box
            sx={{
              mt: 'auto',
              pt: 4,
              pb: 2,
              px: 2,
              borderTop: `1px solid ${alpha(theme.palette.divider, 0.1)}`,
            }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
              Version 1.0.0
            </Typography>
            <Typography variant="caption" color="text.secondary">
              © 2025 Lavacake
            </Typography>
          </Box>
        </Box>
      </Drawer>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          backgroundColor: theme.palette.background.default,
          minHeight: '100vh',
        }}
      >
        <Toolbar /> {/* Spacer for AppBar */}
        {children}
      </Box>
    </Box>
  );
};

export default Layout;
