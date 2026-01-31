import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Slider,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { useViewStyle } from '../../contexts/ViewStyleContext';

interface ViewStyleSettingsProps {
  open: boolean;
  onClose: () => void;
}

const fontFamilies = [
  { value: 'Georgia, serif', label: 'Georgia' },
  { value: 'Times New Roman, serif', label: 'Times New Roman' },
  { value: 'Arial, sans-serif', label: 'Arial' },
  { value: 'Verdana, sans-serif', label: 'Verdana' },
  { value: 'Roboto, sans-serif', label: 'Roboto' },
  { value: 'monospace', label: 'Monospace' },
];

export function ViewStyleSettings({ open, onClose }: ViewStyleSettingsProps) {
  const { style, updateStyle } = useViewStyle();

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Reading Settings</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 2 }}>
          <Typography gutterBottom>Font Size: {style.fontSize}px</Typography>
          <Slider
            value={style.fontSize}
            onChange={(_, v) => updateStyle({ fontSize: v as number })}
            min={12}
            max={24}
            step={1}
            marks
          />

          <Typography gutterBottom sx={{ mt: 2 }}>
            Line Height: {style.lineHeight}
          </Typography>
          <Slider
            value={style.lineHeight}
            onChange={(_, v) => updateStyle({ lineHeight: v as number })}
            min={1.2}
            max={2.5}
            step={0.1}
          />

          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Font Family</InputLabel>
            <Select
              value={style.fontFamily}
              label="Font Family"
              onChange={(e) => updateStyle({ fontFamily: e.target.value })}
            >
              {fontFamilies.map((f) => (
                <MenuItem key={f.value} value={f.value} sx={{ fontFamily: f.value }}>
                  {f.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Typography gutterBottom sx={{ mt: 2 }}>
            Color Theme
          </Typography>
          <ToggleButtonGroup
            value={style.colorSet}
            exclusive
            onChange={(_, v) => v && updateStyle({ colorSet: v })}
            fullWidth
          >
            <ToggleButton value="light" sx={{ bgcolor: '#ffffff', color: '#333' }}>
              Light
            </ToggleButton>
            <ToggleButton value="sepia" sx={{ bgcolor: '#f5f0e1', color: '#5c4b37' }}>
              Sepia
            </ToggleButton>
            <ToggleButton value="dark" sx={{ bgcolor: '#1a1a1a', color: '#e0e0e0' }}>
              Dark
            </ToggleButton>
          </ToggleButtonGroup>

          <Typography gutterBottom sx={{ mt: 2 }}>
            Margin Size: {style.marginSize}px
          </Typography>
          <Slider
            value={style.marginSize}
            onChange={(_, v) => updateStyle({ marginSize: v as number })}
            min={16}
            max={80}
            step={8}
          />

          {/* Preview */}
          <Box
            sx={{
              mt: 3,
              p: 2,
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              bgcolor: style.colorSet === 'dark' ? '#1a1a1a' : style.colorSet === 'sepia' ? '#f5f0e1' : '#ffffff',
              color: style.colorSet === 'dark' ? '#e0e0e0' : style.colorSet === 'sepia' ? '#5c4b37' : '#333333',
            }}
          >
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Preview
            </Typography>
            <Typography
              sx={{
                fontSize: style.fontSize,
                lineHeight: style.lineHeight,
                fontFamily: style.fontFamily,
                px: style.marginSize / 10,
              }}
            >
              This is a sample text to preview your reading settings. The quick brown fox jumps over the lazy dog.
            </Typography>
          </Box>
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
}
