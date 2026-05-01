import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper as MuiPaper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  TextField,
  Chip,
  IconButton,
  CircularProgress,
  Button,
  Autocomplete,
} from '@mui/material';
import { Search, Refresh, Upload } from '@mui/icons-material';
import type { Paper, PaperFilter } from '../../types';
import { paperService } from '../../services/api';

export function PaperList() {
  const navigate = useNavigate();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter] = useState<PaperFilter>({});
  const [searchText, setSearchText] = useState('');
  const [allTags, setAllTags] = useState<string[]>([]);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);

  const loadPapers = async () => {
    setLoading(true);
    try {
      const response = await paperService.getPapers({
        ...filter,
        tags: selectedTags.length > 0 ? selectedTags : undefined,
      });
      setPapers(response.papers);
      
      // Collect all unique tags
      const tags = new Set<string>();
      response.papers.forEach((p) => p.tags.forEach((t) => tags.add(t)));
      setAllTags(Array.from(tags));
    } catch (error) {
      console.error('Failed to load papers:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPapers();
  }, [filter, selectedTags]);

  const filteredPapers = papers.filter((paper) => {
    if (!searchText) return true;
    const search = searchText.toLowerCase();
    return (
      paper.title.toLowerCase().includes(search) ||
      paper.authors.some((a) => a.toLowerCase().includes(search)) ||
      paper.description.toLowerCase().includes(search)
    );
  });

  return (
    <Box sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Papers</Typography>
        <Box>
          <Button
            variant="contained"
            startIcon={<Upload />}
            onClick={() => navigate('/upload')}
            sx={{ mr: 1 }}
          >
            Upload Paper
          </Button>
          <IconButton onClick={loadPapers}>
            <Refresh />
          </IconButton>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', gap: 2, mb: 3 }}>
        <TextField
          placeholder="Search papers..."
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          InputProps={{
            startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
          }}
          sx={{ flexGrow: 1 }}
        />
        <Autocomplete
          multiple
          options={allTags}
          value={selectedTags}
          onChange={(_, newValue) => setSelectedTags(newValue)}
          renderInput={(params) => (
            <TextField {...params} placeholder="Filter by tags" />
          )}
          sx={{ minWidth: 250 }}
        />
      </Box>

      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={MuiPaper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Title</TableCell>
                <TableCell>Authors</TableCell>
                <TableCell>Tags</TableCell>
                <TableCell>Created</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredPapers.map((paper) => (
                <TableRow
                  key={paper.id}
                  hover
                  sx={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/papers/${paper.id}`)}
                >
                  <TableCell>
                    <Typography variant="subtitle1">{paper.title}</Typography>
                    <Typography variant="body2" color="text.secondary" noWrap sx={{ maxWidth: 400 }}>
                      {paper.description}
                    </Typography>
                  </TableCell>
                  <TableCell>{paper.authors.join(', ')}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {paper.tags.map((tag) => (
                        <Chip key={tag} label={tag} size="small" />
                      ))}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {new Date(paper.createdAt).toLocaleDateString()}
                  </TableCell>
                </TableRow>
              ))}
              {filteredPapers.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} align="center">
                    <Typography color="text.secondary">No papers found</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
