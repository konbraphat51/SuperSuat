import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { ViewStyleProvider } from './contexts/ViewStyleContext';
import { HighlightProvider } from './contexts/HighlightContext';
import { PaperList } from './components/PaperList';
import { PaperReader } from './components/PaperReader';
import { PaperUpload } from './components/PaperUpload';
import { PaperMetaEdit } from './components/PaperMetaEdit';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <ViewStyleProvider>
        <HighlightProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<PaperList />} />
              <Route path="/papers/:paperId" element={<PaperReader />} />
              <Route path="/papers/:paperId/edit" element={<PaperMetaEdit />} />
              <Route path="/upload" element={<PaperUpload />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </BrowserRouter>
        </HighlightProvider>
      </ViewStyleProvider>
    </ThemeProvider>
  );
}

export default App;
