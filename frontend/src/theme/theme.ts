import { createTheme } from '@mui/material/styles';

// Fashion-forward color palette
const colors = {
  // Primary palette
  blushRose: '#FFE5E5',
  dustyRose: '#F4A5B9',
  mauve: '#D4A5D4',
  sageGreen: '#C4D9C4',
  warmCream: '#FAF8F5',
  charcoal: '#2D2D2D',
  softGray: '#E8E4E1',

  // Accent colors
  coral: '#FF9B9B',
  lavender: '#E0D5F5',
  champagne: '#F5F0E8',
  white: '#FFFFFF',
};

// Create custom theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: colors.dustyRose,
      light: colors.blushRose,
      dark: '#E08FA2',
      contrastText: colors.white,
    },
    secondary: {
      main: colors.mauve,
      light: colors.lavender,
      dark: '#C28FC2',
      contrastText: colors.white,
    },
    success: {
      main: colors.sageGreen,
      light: '#D9E8D9',
      dark: '#A8C4A8',
    },
    error: {
      main: colors.coral,
      light: '#FFB5B5',
      dark: '#E68585',
    },
    warning: {
      main: '#FFD699',
      light: '#FFE5B8',
      dark: '#E6C280',
    },
    info: {
      main: colors.lavender,
      light: '#F0E8FA',
      dark: '#C8B8E0',
    },
    background: {
      default: colors.warmCream,
      paper: colors.white,
    },
    text: {
      primary: colors.charcoal,
      secondary: 'rgba(45, 45, 45, 0.7)',
      disabled: 'rgba(45, 45, 45, 0.4)',
    },
    divider: colors.softGray,
  },
  typography: {
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    h1: {
      fontFamily: "'Playfair Display', serif",
      fontSize: '2.5rem',
      fontWeight: 600,
      letterSpacing: '-0.5px',
      color: colors.charcoal,
    },
    h2: {
      fontFamily: "'Playfair Display', serif",
      fontSize: '2rem',
      fontWeight: 600,
      letterSpacing: '-0.5px',
      color: colors.charcoal,
    },
    h3: {
      fontFamily: "'Playfair Display', serif",
      fontSize: '1.75rem',
      fontWeight: 600,
      color: colors.charcoal,
    },
    h4: {
      fontFamily: "'Playfair Display', serif",
      fontSize: '1.5rem',
      fontWeight: 600,
      color: colors.charcoal,
    },
    h5: {
      fontFamily: "'Inter', sans-serif",
      fontSize: '1.25rem',
      fontWeight: 600,
      color: colors.charcoal,
    },
    h6: {
      fontFamily: "'Inter', sans-serif",
      fontSize: '1rem',
      fontWeight: 600,
      color: colors.charcoal,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.6,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
      letterSpacing: '0.5px',
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
    '0 2px 8px rgba(244, 165, 185, 0.1)',
    '0 4px 16px rgba(244, 165, 185, 0.15)',
    '0 8px 32px rgba(244, 165, 185, 0.2)',
    '0 12px 40px rgba(244, 165, 185, 0.25)',
  ],
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: '9999px',
          padding: '10px 24px',
          boxShadow: '0 2px 8px rgba(244, 165, 185, 0.1)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: '0 4px 16px rgba(244, 165, 185, 0.2)',
          },
        },
        contained: {
          background: `linear-gradient(135deg, ${colors.dustyRose}, ${colors.mauve})`,
          '&:hover': {
            background: `linear-gradient(135deg, #E08FA2, #C28FC2)`,
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: '16px',
          boxShadow: '0 4px 16px rgba(244, 165, 185, 0.15)',
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(10px)',
          transition: 'all 0.3s ease',
          '&:hover': {
            boxShadow: '0 8px 32px rgba(244, 165, 185, 0.2)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: '16px',
          boxShadow: '0 4px 16px rgba(244, 165, 185, 0.15)',
        },
        elevation1: {
          boxShadow: '0 2px 8px rgba(244, 165, 185, 0.1)',
        },
        elevation2: {
          boxShadow: '0 4px 16px rgba(244, 165, 185, 0.15)',
        },
        elevation3: {
          boxShadow: '0 8px 32px rgba(244, 165, 185, 0.2)',
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: '9999px',
          fontWeight: 500,
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: '12px',
            '&:hover fieldset': {
              borderColor: colors.dustyRose,
            },
            '&.Mui-focused fieldset': {
              borderColor: colors.dustyRose,
              borderWidth: '2px',
            },
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          background: colors.white,
          borderRight: `1px solid ${colors.softGray}`,
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: '8px',
          margin: '4px 8px',
          transition: 'all 0.2s ease',
          '&.Mui-selected': {
            background: `linear-gradient(135deg, ${colors.blushRose}, ${colors.champagne})`,
            '&:hover': {
              background: `linear-gradient(135deg, ${colors.blushRose}, ${colors.champagne})`,
            },
          },
          '&:hover': {
            background: colors.blushRose,
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          background: colors.white,
          color: colors.charcoal,
          boxShadow: '0 2px 8px rgba(244, 165, 185, 0.1)',
        },
      },
    },
  },
});

export default theme;
