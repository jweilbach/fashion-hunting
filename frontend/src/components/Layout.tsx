import React, { useState } from 'react';
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
  Collapse,
} from '@mui/material';
import {
  Dashboard as DashboardIcon,
  RssFeed as FeedsIcon,
  Business as BrandIcon,
  WorkOutline as JobsIcon,
  Assessment as ReportsIcon,
  History as HistoryIcon,
  LogoutOutlined as LogoutIcon,
  ChevronRight as ChevronRightIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material';
import { useAuth } from '../context/AuthContext';
import { PROVIDER_CATEGORIES } from '../config/providers';

const drawerWidth = 260;

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const theme = useTheme();

  // Expansion state for Reports menu and its submenus
  const [reportsExpanded, setReportsExpanded] = useState(() => {
    // Auto-expand if we're on a reports page
    return location.pathname.startsWith('/reports/');
  });
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(() => {
    // Auto-expand the category if we're viewing a provider within it
    const expanded = new Set<string>();
    PROVIDER_CATEGORIES.forEach(category => {
      category.providers.forEach(provider => {
        if (location.pathname.includes(`/reports/${category.id}/${provider.route}`)) {
          expanded.add(category.id);
        }
      });
    });
    return expanded;
  });

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const toggleReportsExpanded = () => {
    setReportsExpanded(!reportsExpanded);
  };

  const toggleCategoryExpanded = (categoryId: string) => {
    setExpandedCategories(prev => {
      const newSet = new Set(prev);
      if (newSet.has(categoryId)) {
        newSet.delete(categoryId);
      } else {
        newSet.add(categoryId);
      }
      return newSet;
    });
  };

  // Check if current path matches a reports provider
  const isReportsProviderActive = (categoryId: string, providerRoute: string) => {
    return location.pathname === `/reports/${categoryId}/${providerRoute}`;
  };

  // Check if any provider in a category is active
  const isCategoryActive = (categoryId: string) => {
    return location.pathname.startsWith(`/reports/${categoryId}/`);
  };

  // Check if we're on any reports page
  const isReportsActive = location.pathname.startsWith('/reports/');

  const menuItems = [
    { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
    { text: 'Brands', icon: <BrandIcon />, path: '/brands' },
    { text: 'Feeds', icon: <FeedsIcon />, path: '/feeds' },
    { text: 'Jobs', icon: <JobsIcon />, path: '/jobs' },
    { text: 'History', icon: <HistoryIcon />, path: '/history' },
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
                      slotProps={{
                        primary: {
                          fontWeight: isSelected ? 600 : 500,
                          fontSize: '0.95rem',
                        },
                      }}
                    />
                  </ListItemButton>
                </ListItem>
              );
            })}

            {/* Reports - Expandable Section */}
            <ListItem disablePadding sx={{ mb: 0.5 }}>
              <ListItemButton
                onClick={toggleReportsExpanded}
                sx={{
                  borderRadius: 2,
                  transition: 'all 0.3s ease',
                  ...(isReportsActive && {
                    background: `linear-gradient(135deg, ${alpha(theme.palette.primary.main, 0.15)}, ${alpha(theme.palette.secondary.main, 0.15)})`,
                    boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.2)}`,
                  }),
                  ...(!isReportsActive && {
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
                    color: isReportsActive ? theme.palette.primary.main : theme.palette.text.secondary,
                  }}
                >
                  <ReportsIcon />
                </ListItemIcon>
                <ListItemText
                  primary="Reports"
                  slotProps={{
                    primary: {
                      fontWeight: isReportsActive ? 600 : 500,
                      fontSize: '0.95rem',
                    },
                  }}
                />
                {reportsExpanded ? (
                  <ExpandMoreIcon sx={{ color: theme.palette.text.secondary, fontSize: 20 }} />
                ) : (
                  <ChevronRightIcon sx={{ color: theme.palette.text.secondary, fontSize: 20 }} />
                )}
              </ListItemButton>
            </ListItem>

            {/* Reports Submenu - Categories */}
            <Collapse in={reportsExpanded} timeout="auto" unmountOnExit>
              <List component="div" disablePadding sx={{ pl: 2 }}>
                {PROVIDER_CATEGORIES.map((category) => {
                  const categoryActive = isCategoryActive(category.id);
                  const categoryExpanded = expandedCategories.has(category.id);

                  return (
                    <Box key={category.id}>
                      {/* Category Header */}
                      <ListItem disablePadding sx={{ mb: 0.25 }}>
                        <ListItemButton
                          onClick={() => toggleCategoryExpanded(category.id)}
                          sx={{
                            borderRadius: 2,
                            py: 0.75,
                            transition: 'all 0.2s ease',
                            ...(categoryActive && {
                              background: alpha(theme.palette.primary.main, 0.08),
                            }),
                            '&:hover': {
                              background: alpha(theme.palette.primary.main, 0.08),
                              transform: 'translateX(4px)',
                            },
                          }}
                        >
                          <ListItemText
                            primary={category.label}
                            slotProps={{
                              primary: {
                                fontWeight: categoryActive ? 600 : 500,
                                fontSize: '0.9rem',
                                color: categoryActive ? theme.palette.primary.main : theme.palette.text.secondary,
                              },
                            }}
                          />
                          {categoryExpanded ? (
                            <ExpandMoreIcon sx={{ color: theme.palette.text.secondary, fontSize: 18 }} />
                          ) : (
                            <ChevronRightIcon sx={{ color: theme.palette.text.secondary, fontSize: 18 }} />
                          )}
                        </ListItemButton>
                      </ListItem>

                      {/* Provider Items */}
                      <Collapse in={categoryExpanded} timeout="auto" unmountOnExit>
                        <List component="div" disablePadding sx={{ pl: 2 }}>
                          {category.providers.map((provider) => {
                            const providerActive = isReportsProviderActive(category.id, provider.route);
                            const ProviderIcon = provider.icon;

                            return (
                              <ListItem key={provider.id} disablePadding sx={{ mb: 0.25 }}>
                                <ListItemButton
                                  onClick={() => navigate(`/reports/${category.id}/${provider.route}`)}
                                  sx={{
                                    borderRadius: 2,
                                    py: 0.5,
                                    transition: 'all 0.2s ease',
                                    ...(providerActive && {
                                      background: alpha(theme.palette.primary.main, 0.12),
                                    }),
                                    '&:hover': {
                                      background: alpha(theme.palette.primary.main, 0.08),
                                      transform: 'translateX(4px)',
                                    },
                                  }}
                                >
                                  <ListItemIcon
                                    sx={{
                                      minWidth: 32,
                                      color: providerActive ? theme.palette.primary.main : theme.palette.text.secondary,
                                    }}
                                  >
                                    <ProviderIcon sx={{ fontSize: 18 }} />
                                  </ListItemIcon>
                                  <ListItemText
                                    primary={provider.label}
                                    slotProps={{
                                      primary: {
                                        fontWeight: providerActive ? 600 : 400,
                                        fontSize: '0.85rem',
                                        color: providerActive ? theme.palette.primary.main : theme.palette.text.secondary,
                                      },
                                    }}
                                  />
                                </ListItemButton>
                              </ListItem>
                            );
                          })}
                        </List>
                      </Collapse>
                    </Box>
                  );
                })}
              </List>
            </Collapse>
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
