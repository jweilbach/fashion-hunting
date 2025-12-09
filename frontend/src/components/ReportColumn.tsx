import React from 'react';
import {
  Box,
  Typography,
  Chip,
  List,
  ListItem,
  Checkbox,
  Link,
  Stack,
  Paper,
  Button,
  Collapse,
  Pagination,
  Divider,
  alpha,
  useTheme,
} from '@mui/material';
import { ExpandMore as ExpandMoreIcon, AccessTime as TimeIcon } from '@mui/icons-material';
import { motion } from 'framer-motion';
import type { Report } from '../types';

interface ReportColumnProps {
  title: string;
  icon: React.ReactNode;
  reports: Report[];
  totalCount: number;
  color: string;
  expandedReports: Set<string>;
  selectedReports: Set<string>;
  onToggleExpansion: (id: string) => void;
  onToggleSelection: (id: string) => void;
  onPageChange: (page: number) => void;
  currentPage: number;
  getSentimentColor: (sentiment: string) => "default" | "success" | "error" | "warning" | "primary" | "secondary" | "info";
  knownBrandNames: Set<string>;
  sortBrands: (brands: string[]) => string[];
}

export const ReportColumn: React.FC<ReportColumnProps> = ({
  title,
  icon,
  reports,
  totalCount,
  color,
  expandedReports,
  selectedReports,
  onToggleExpansion,
  onToggleSelection,
  onPageChange,
  currentPage,
  getSentimentColor,
  knownBrandNames,
  sortBrands,
}) => {
  const theme = useTheme();
  const itemsPerPage = 10;

  // Server-side pagination calculations
  const totalPages = Math.ceil(totalCount / itemsPerPage);

  return (
    <Box flex={1} display="flex" flexDirection="column">
      {/* Header */}
      <Box
        sx={{
          p: 2,
          mb: 2,
          borderRadius: 2,
          backgroundColor: alpha(color, 0.08),
          border: `2px solid ${alpha(color, 0.2)}`,
        }}
      >
        <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
          <Box display="flex" alignItems="center" gap={1.5}>
            <Box sx={{ color }}>{icon}</Box>
            <Typography variant="h6" sx={{ fontWeight: 600, color }}>
              {title}
            </Typography>
            <Chip
              label={totalCount}
              size="small"
              sx={{
                backgroundColor: color,
                color: 'white',
                fontWeight: 600,
              }}
            />
          </Box>
        </Box>
        {totalPages > 1 && (
          <Box display="flex" justifyContent="center" mt={1}>
            <Pagination
              count={totalPages}
              page={currentPage}
              onChange={(_, newPage) => onPageChange(newPage)}
              size="small"
              color="primary"
            />
          </Box>
        )}
      </Box>

      {/* Scrollable List */}
      <Box sx={{ flex: 1, overflowY: 'auto', pr: 1 }}>
        <List sx={{ p: 0 }}>
          {reports.map((report, index) => {
            const isExpanded = expandedReports.has(report.id);
            const isSelected = selectedReports.has(report.id);

            return (
              <React.Fragment key={report.id}>
                <motion.div
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                >
                  <ListItem
                    sx={{
                      borderLeft: `4px solid ${color}`,
                      borderRadius: 2,
                      mb: 1,
                      backgroundColor: isSelected ? alpha(color, 0.05) : 'transparent',
                      transition: 'all 0.2s',
                      '&:hover': {
                        backgroundColor: alpha(color, 0.08),
                      },
                    }}
                  >
                    <Box display="flex" alignItems="flex-start" width="100%">
                      <Checkbox
                        checked={isSelected}
                        onChange={() => onToggleSelection(report.id)}
                        size="small"
                        sx={{ mt: 0.5, mr: 1 }}
                      />
                      <Box flex={1}>
                        <Box display="flex" alignItems="center" gap={1} mb={1} flexWrap="wrap">
                          <Link
                            href={report.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            underline="hover"
                            color="inherit"
                            sx={{ fontWeight: 600, fontSize: '1.05rem' }}
                          >
                            {report.title}
                          </Link>
                          <Chip
                            label={report.sentiment}
                            color={getSentimentColor(report.sentiment)}
                            size="small"
                            sx={{ fontWeight: 500 }}
                          />
                        </Box>

                        <Stack direction="row" spacing={2} mb={1.5} alignItems="center" flexWrap="wrap">
                          <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <TimeIcon sx={{ fontSize: 16 }} />
                            Published: {new Date(report.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </Typography>
                          <Typography variant="body2" color="text.secondary" sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            •
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            Found: {new Date(report.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                          </Typography>
                          <Chip label={report.source} size="small" variant="outlined" />
                        </Stack>

                        {report.brands && report.brands.length > 0 && (
                          <Box mb={1.5}>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5, fontWeight: 600 }}>
                              Brands Mentioned:
                            </Typography>
                            {sortBrands(report.brands).map((brand, idx) => {
                              const isKnown = knownBrandNames.has(brand);
                              return (
                                <Chip
                                  key={idx}
                                  label={brand}
                                  size="small"
                                  variant={isKnown ? 'filled' : 'outlined'}
                                  color={isKnown ? 'success' : 'default'}
                                  sx={{
                                    mr: 0.5,
                                    mb: 0.5,
                                    fontWeight: isKnown ? 600 : 400,
                                  }}
                                />
                              );
                            })}
                          </Box>
                        )}

                        {report.summary && (
                          <Box>
                            <Collapse in={isExpanded} collapsedSize={60}>
                              <Paper
                                elevation={0}
                                sx={{
                                  backgroundColor: alpha(theme.palette.primary.light, 0.08),
                                  p: 2,
                                  borderRadius: 2,
                                }}
                              >
                                <Typography variant="body2" color="text.secondary">
                                  {report.summary}
                                </Typography>
                              </Paper>
                            </Collapse>
                            <Button
                              size="small"
                              onClick={() => onToggleExpansion(report.id)}
                              sx={{ mt: 1 }}
                              endIcon={
                                <ExpandMoreIcon
                                  sx={{
                                    transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                                    transition: 'transform 0.3s',
                                  }}
                                />
                              }
                            >
                              {isExpanded ? 'Show Less' : 'Read More'}
                            </Button>
                          </Box>
                        )}
                      </Box>
                    </Box>
                  </ListItem>
                </motion.div>
                {index < reports.length - 1 && (
                  <Divider sx={{ my: 1.5, borderColor: alpha(color, 0.15) }} />
                )}
              </React.Fragment>
            );
          })}
        </List>
      </Box>
    </Box>
  );
};
