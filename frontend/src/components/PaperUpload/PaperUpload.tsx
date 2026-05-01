import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Alert,
} from '@mui/material';
import { CloudUpload } from '@mui/icons-material';
import { paperService } from '../../services/api';

export function PaperUpload() {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0];
    if (selectedFile) {
      if (selectedFile.type !== 'application/pdf') {
        setError('Please select a PDF file');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  };

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    const droppedFile = event.dataTransfer.files[0];
    if (droppedFile) {
      if (droppedFile.type !== 'application/pdf') {
        setError('Please drop a PDF file');
        return;
      }
      setFile(droppedFile);
      setError(null);
    }
  };

  const handleDragOver = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault();
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setProgress(0);
    setError(null);

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress((prev) => Math.min(prev + 10, 90));
    }, 500);

    try {
      const paper = await paperService.uploadPaper(file);
      clearInterval(progressInterval);
      setProgress(100);

      // Navigate to the paper reader after a short delay
      setTimeout(() => {
        navigate(`/papers/${paper.id}`);
      }, 500);
    } catch (err) {
      clearInterval(progressInterval);
      setError('Failed to upload paper. Please try again.');
      console.error('Upload error:', err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <Box sx={{ p: 3, maxWidth: 600, mx: 'auto' }}>
      <Typography variant="h4" sx={{ mb: 3 }}>
        Upload Paper
      </Typography>

      <Paper
        sx={{
          p: 4,
          border: '2px dashed',
          borderColor: file ? 'primary.main' : 'grey.300',
          borderRadius: 2,
          textAlign: 'center',
          cursor: 'pointer',
          transition: 'border-color 0.3s',
          '&:hover': {
            borderColor: 'primary.light',
          },
        }}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          style={{ display: 'none' }}
          onChange={handleFileSelect}
        />

        <CloudUpload sx={{ fontSize: 64, color: 'grey.400', mb: 2 }} />

        {file ? (
          <>
            <Typography variant="h6" sx={{ mb: 1 }}>
              {file.name}
            </Typography>
            <Typography color="text.secondary">
              {(file.size / 1024 / 1024).toFixed(2)} MB
            </Typography>
          </>
        ) : (
          <>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Drop a PDF file here
            </Typography>
            <Typography color="text.secondary">
              or click to select a file
            </Typography>
          </>
        )}
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      )}

      {uploading && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress variant="determinate" value={progress} />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1, textAlign: 'center' }}>
            {progress < 100 ? 'Processing paper with AI...' : 'Complete!'}
          </Typography>
        </Box>
      )}

      <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
        <Button variant="outlined" onClick={() => navigate('/')} fullWidth>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleUpload}
          disabled={!file || uploading}
          fullWidth
        >
          {uploading ? 'Uploading...' : 'Upload'}
        </Button>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mt: 3, textAlign: 'center' }}>
        The paper will be processed by AI to extract text, figures, tables, and metadata.
        This may take a few minutes for longer papers.
      </Typography>
    </Box>
  );
}
