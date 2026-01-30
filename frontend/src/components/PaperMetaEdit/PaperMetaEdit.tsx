import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Add, Save, ArrowBack } from '@mui/icons-material';
import type { Paper as PaperType } from '../../types';
import { paperService } from '../../services/api';

export function PaperMetaEdit() {
  const { paperId } = useParams<{ paperId: string }>();
  const navigate = useNavigate();
  
  const [paper, setPaper] = useState<PaperType | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [authors, setAuthors] = useState<string[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [originalUrl, setOriginalUrl] = useState('');
  const [newAuthor, setNewAuthor] = useState('');
  const [newTag, setNewTag] = useState('');

  useEffect(() => {
    const loadPaper = async () => {
      if (!paperId) return;
      
      try {
        const data = await paperService.getPaper(paperId);
        setPaper(data);
        setTitle(data.title);
        setDescription(data.description);
        setAuthors(data.authors);
        setTags(data.tags);
        setOriginalUrl(data.originalUrl || '');
      } catch (err) {
        setError('Failed to load paper');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    loadPaper();
  }, [paperId]);

  const handleAddAuthor = () => {
    if (newAuthor.trim() && !authors.includes(newAuthor.trim())) {
      setAuthors([...authors, newAuthor.trim()]);
      setNewAuthor('');
    }
  };

  const handleRemoveAuthor = (author: string) => {
    setAuthors(authors.filter((a) => a !== author));
  };

  const handleAddTag = () => {
    if (newTag.trim() && !tags.includes(newTag.trim())) {
      setTags([...tags, newTag.trim()]);
      setNewTag('');
    }
  };

  const handleRemoveTag = (tag: string) => {
    setTags(tags.filter((t) => t !== tag));
  };

  const handleSave = async () => {
    if (!paperId) return;
    
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await paperService.updatePaper(paperId, {
        title,
        description,
        authors,
        tags,
        originalUrl: originalUrl || undefined,
      });
      setSuccess(true);
    } catch (err) {
      setError('Failed to save changes');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!paper) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography>Paper not found</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button
          startIcon={<ArrowBack />}
          onClick={() => navigate(`/papers/${paperId}`)}
          sx={{ mr: 2 }}
        >
          Back to Paper
        </Button>
        <Typography variant="h4">Edit Metadata</Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Changes saved successfully!
        </Alert>
      )}

      <Paper sx={{ p: 3 }}>
        <TextField
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          fullWidth
          sx={{ mb: 3 }}
        />

        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          fullWidth
          multiline
          rows={3}
          sx={{ mb: 3 }}
        />

        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Authors
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {authors.map((author) => (
            <Chip
              key={author}
              label={author}
              onDelete={() => handleRemoveAuthor(author)}
            />
          ))}
        </Box>
        <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
          <TextField
            size="small"
            placeholder="Add author"
            value={newAuthor}
            onChange={(e) => setNewAuthor(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddAuthor()}
          />
          <Button
            variant="outlined"
            size="small"
            startIcon={<Add />}
            onClick={handleAddAuthor}
          >
            Add
          </Button>
        </Box>

        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          Tags
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
          {tags.map((tag) => (
            <Chip
              key={tag}
              label={tag}
              onDelete={() => handleRemoveTag(tag)}
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
        <Box sx={{ display: 'flex', gap: 1, mb: 3 }}>
          <TextField
            size="small"
            placeholder="Add tag"
            value={newTag}
            onChange={(e) => setNewTag(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddTag()}
          />
          <Button
            variant="outlined"
            size="small"
            startIcon={<Add />}
            onClick={handleAddTag}
          >
            Add
          </Button>
        </Box>

        <TextField
          label="Original URL"
          value={originalUrl}
          onChange={(e) => setOriginalUrl(e.target.value)}
          fullWidth
          placeholder="https://arxiv.org/abs/..."
          sx={{ mb: 3 }}
        />

        <Button
          variant="contained"
          startIcon={<Save />}
          onClick={handleSave}
          disabled={saving}
          fullWidth
        >
          {saving ? 'Saving...' : 'Save Changes'}
        </Button>
      </Paper>
    </Box>
  );
}
