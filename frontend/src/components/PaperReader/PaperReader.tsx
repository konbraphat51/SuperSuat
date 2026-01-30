import { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Paper,
  Typography,
  Drawer,
  IconButton,
  Tabs,
  Tab,
  CircularProgress,
  Tooltip,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Divider,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Button,
} from '@mui/material';
import {
  Menu as MenuIcon,
  FormatListBulleted,
  Highlight as HighlightIcon,
  Summarize,
  Chat,
  Settings,
} from '@mui/icons-material';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import type { PaperDetail, Translation, Summary, ChatMessage } from '../../types';
import { paperService, translationService, summaryService, chatService } from '../../services/api';
import { useViewStyle } from '../../contexts/ViewStyleContext';
import { useHighlight } from '../../contexts/HighlightContext';
import { ViewStyleSettings } from './ViewStyleSettings';

const DRAWER_WIDTH = 320;

export function PaperReader() {
  const { paperId } = useParams<{ paperId: string }>();
  const { style } = useViewStyle();
  const { highlights, loadHighlights, selectedColor, addHighlight } = useHighlight();

  const [paper, setPaper] = useState<PaperDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(true);
  const [sidebarTab, setSidebarTab] = useState(0);

  // Translation state
  const [availableLanguages, setAvailableLanguages] = useState<string[]>([]);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const [translation, setTranslation] = useState<Translation | null>(null);
  const [loadingTranslation, setLoadingTranslation] = useState(false);

  // Summary state
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);

  // Chat state
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [loadingChat, setLoadingChat] = useState(false);

  // Settings state
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (!paperId) return;

    const loadPaper = async () => {
      setLoading(true);
      try {
        const data = await paperService.getPaper(paperId);
        setPaper(data);
        
        // Load highlights
        await loadHighlights(paperId);
        
        // Load available languages
        const languages = await translationService.getAvailableLanguages(paperId);
        setAvailableLanguages(languages);
      } catch (error) {
        console.error('Failed to load paper:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPaper();
  }, [paperId, loadHighlights]);

  const handleLanguageChange = async (language: string) => {
    setSelectedLanguage(language);
    if (!language || !paperId) {
      setTranslation(null);
      return;
    }

    setLoadingTranslation(true);
    try {
      const trans = await translationService.getTranslation(paperId, language);
      setTranslation(trans);
    } catch {
      // Translation might not exist, try to create
      try {
        const trans = await translationService.createTranslation(paperId, language);
        setTranslation(trans);
      } catch (error) {
        console.error('Failed to load/create translation:', error);
      }
    } finally {
      setLoadingTranslation(false);
    }
  };

  const loadSummary = async (language: string = 'en') => {
    if (!paperId) return;
    
    setLoadingSummary(true);
    try {
      const sum = await summaryService.getSummary(paperId, language);
      setSummary(sum);
    } catch {
      // Summary might not exist, try to create
      try {
        const sum = await summaryService.createSummary(paperId, language, true);
        setSummary(sum);
      } catch (error) {
        console.error('Failed to load/create summary:', error);
      }
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleSendChat = async () => {
    if (!chatInput.trim() || !paperId) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatMessages((prev) => [...prev, { role: 'user', content: userMessage }]);

    setLoadingChat(true);
    try {
      const response = await chatService.sendMessage(paperId, userMessage);
      setChatMessages((prev) => [...prev, { role: 'assistant', content: response }]);
    } catch (error) {
      console.error('Failed to send chat message:', error);
    } finally {
      setLoadingChat(false);
    }
  };

  const handleTextSelection = useCallback(() => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || !paperId) return;

    const range = selection.getRangeAt(0);
    const container = range.startContainer.parentElement;
    if (!container) return;

    const paragraphElement = container.closest('[data-paragraph-id]');
    if (!paragraphElement) return;

    const paragraphId = paragraphElement.getAttribute('data-paragraph-id');
    if (!paragraphId) return;

    // Calculate offsets relative to the paragraph
    const startOffset = range.startOffset;
    const endOffset = range.endOffset;

    addHighlight(paperId, {
      paragraphId,
      startOffset,
      endOffset,
      color: selectedColor,
    });

    selection.removeAllRanges();
  }, [paperId, selectedColor, addHighlight]);

  const scrollToSection = (sectionId: string) => {
    const element = document.getElementById(`section-${sectionId}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const scrollToHighlight = (highlightId: string) => {
    const element = document.querySelector(`[data-highlight-id="${highlightId}"]`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const getTranslatedParagraph = (paragraphId: string): string | null => {
    if (!translation) return null;
    for (const section of translation.sections) {
      const para = section.paragraphs.find((p) => p.paragraphId === paragraphId);
      if (para) return para.translatedContent;
    }
    return null;
  };

  const colorSetStyles = useMemo(() => {
    switch (style.colorSet) {
      case 'dark':
        return { bgcolor: '#1a1a1a', color: '#e0e0e0' };
      case 'sepia':
        return { bgcolor: '#f5f0e1', color: '#5c4b37' };
      default:
        return { bgcolor: '#ffffff', color: '#333333' };
    }
  }, [style.colorSet]);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
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
    <Box sx={{ display: 'flex', height: '100vh' }}>
      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          ml: drawerOpen ? `${DRAWER_WIDTH}px` : 0,
          transition: 'margin 0.3s',
          ...colorSetStyles,
          overflow: 'auto',
        }}
        onMouseUp={handleTextSelection}
      >
        {/* Toolbar */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
          <IconButton onClick={() => setDrawerOpen(!drawerOpen)}>
            <MenuIcon />
          </IconButton>
          
          <FormControl size="small" sx={{ minWidth: 150, ml: 2 }}>
            <InputLabel>Language</InputLabel>
            <Select
              value={selectedLanguage}
              label="Language"
              onChange={(e) => handleLanguageChange(e.target.value)}
            >
              <MenuItem value="">Original</MenuItem>
              {availableLanguages.map((lang) => (
                <MenuItem key={lang} value={lang}>{lang}</MenuItem>
              ))}
              <MenuItem value="ja">Japanese (Create)</MenuItem>
              <MenuItem value="zh">Chinese (Create)</MenuItem>
              <MenuItem value="ko">Korean (Create)</MenuItem>
            </Select>
          </FormControl>

          {loadingTranslation && <CircularProgress size={20} sx={{ ml: 2 }} />}

          <Box sx={{ flexGrow: 1 }} />

          <IconButton onClick={() => setSettingsOpen(true)}>
            <Settings />
          </IconButton>
        </Box>

        {/* Paper content */}
        <Paper sx={{ p: style.marginSize / 10, ...colorSetStyles }}>
          <Typography variant="h4" sx={{ mb: 2, fontFamily: style.fontFamily }}>
            {paper.title}
          </Typography>
          
          <Typography variant="subtitle1" color="text.secondary" sx={{ mb: 4 }}>
            {paper.authors.join(', ')}
          </Typography>

          {paper.content.sections.map((section) => (
            <Box key={section.id} id={`section-${section.id}`} sx={{ mb: 4 }}>
              <Typography
                variant={section.level === 1 ? 'h5' : 'h6'}
                sx={{ mb: 2, fontFamily: style.fontFamily }}
              >
                {translation?.sections.find((s) => s.sectionId === section.id)?.translatedTitle || section.title}
              </Typography>

              {section.paragraphs.map((para) => {
                const translatedContent = getTranslatedParagraph(para.id);
                
                if (para.type === 'Equation') {
                  return (
                    <Box
                      key={para.id}
                      sx={{ my: 2, textAlign: 'center' }}
                      dangerouslySetInnerHTML={{
                        __html: katex.renderToString(para.content, {
                          displayMode: true,
                          throwOnError: false,
                        }),
                      }}
                    />
                  );
                }

                const paragraphHighlights = highlights.filter((h) => h.paragraphId === para.id);

                return (
                  <Box key={para.id} sx={{ position: 'relative', mb: 2 }}>
                    <Typography
                      data-paragraph-id={para.id}
                      sx={{
                        fontSize: style.fontSize,
                        lineHeight: style.lineHeight,
                        fontFamily: style.fontFamily,
                      }}
                    >
                      {para.content}
                    </Typography>

                    {translatedContent && (
                      <Tooltip title={translatedContent} arrow placement="bottom">
                        <Typography
                          variant="body2"
                          sx={{
                            mt: 1,
                            p: 1,
                            bgcolor: 'action.hover',
                            borderRadius: 1,
                            cursor: 'pointer',
                          }}
                        >
                          📖 Show translation
                        </Typography>
                      </Tooltip>
                    )}

                    {/* Highlight overlays */}
                    {paragraphHighlights.map((hl) => (
                      <Box
                        key={hl.id}
                        data-highlight-id={hl.id}
                        sx={{
                          position: 'absolute',
                          bgcolor: hl.color,
                          opacity: 0.3,
                          pointerEvents: 'none',
                        }}
                      />
                    ))}
                  </Box>
                );
              })}
            </Box>
          ))}

          {/* Figures */}
          {paper.figures.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="h6">Figures</Typography>
              {paper.figures.map((fig) => (
                <Box key={fig.id} sx={{ my: 2, textAlign: 'center' }}>
                  <img src={fig.imageUrl} alt={fig.caption} style={{ maxWidth: '100%' }} />
                  <Typography variant="caption" display="block">
                    {fig.caption}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}

          {/* Tables */}
          {paper.tables.length > 0 && (
            <Box sx={{ mt: 4 }}>
              <Typography variant="h6">Tables</Typography>
              {paper.tables.map((tbl) => (
                <Box key={tbl.id} sx={{ my: 2 }}>
                  <Typography variant="caption" display="block" sx={{ mb: 1 }}>
                    {tbl.caption}
                  </Typography>
                  <div dangerouslySetInnerHTML={{ __html: tbl.content }} />
                </Box>
              ))}
            </Box>
          )}
        </Paper>
      </Box>

      {/* Sidebar drawer */}
      <Drawer
        variant="persistent"
        anchor="left"
        open={drawerOpen}
        sx={{
          width: DRAWER_WIDTH,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: DRAWER_WIDTH,
            boxSizing: 'border-box',
          },
        }}
      >
        <Box sx={{ p: 2 }}>
          <Typography variant="h6" noWrap>
            {paper.title}
          </Typography>
        </Box>
        <Divider />
        
        <Tabs value={sidebarTab} onChange={(_, v) => setSidebarTab(v)} variant="fullWidth">
          <Tab icon={<FormatListBulleted />} aria-label="sections" />
          <Tab icon={<HighlightIcon />} aria-label="highlights" />
          <Tab icon={<Summarize />} aria-label="summary" />
          <Tab icon={<Chat />} aria-label="chat" />
        </Tabs>

        <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
          {/* Sections Tab */}
          {sidebarTab === 0 && (
            <List dense>
              {paper.content.sections.map((section) => (
                <ListItem key={section.id} disablePadding>
                  <ListItemButton
                    onClick={() => scrollToSection(section.id)}
                    sx={{ pl: section.level * 2 }}
                  >
                    <ListItemText primary={section.title} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          )}

          {/* Highlights Tab */}
          {sidebarTab === 1 && (
            <List dense>
              {highlights.length === 0 ? (
                <ListItem>
                  <ListItemText
                    primary="No highlights yet"
                    secondary="Select text to create a highlight"
                  />
                </ListItem>
              ) : (
                highlights.map((hl) => (
                  <ListItem key={hl.id} disablePadding>
                    <ListItemButton onClick={() => scrollToHighlight(hl.id)}>
                      <Box
                        sx={{
                          width: 16,
                          height: 16,
                          bgcolor: hl.color,
                          borderRadius: 1,
                          mr: 1,
                        }}
                      />
                      <ListItemText
                        primary={hl.note || 'Highlight'}
                        secondary={new Date(hl.createdAt).toLocaleDateString()}
                      />
                    </ListItemButton>
                  </ListItem>
                ))
              )}
            </List>
          )}

          {/* Summary Tab */}
          {sidebarTab === 2 && (
            <Box sx={{ p: 1 }}>
              {!summary && !loadingSummary && (
                <Button variant="outlined" onClick={() => loadSummary()} fullWidth>
                  Load Summary
                </Button>
              )}
              {loadingSummary && <CircularProgress size={24} />}
              {summary && (
                <>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>
                    Overall Summary
                  </Typography>
                  <Typography variant="body2" sx={{ mb: 2 }}>
                    {summary.wholeSummary}
                  </Typography>
                  {summary.chapterSummaries && summary.chapterSummaries.length > 0 && (
                    <>
                      <Typography variant="subtitle2" sx={{ mb: 1 }}>
                        Chapter Summaries
                      </Typography>
                      {summary.chapterSummaries.map((cs) => (
                        <Box key={cs.sectionId} sx={{ mb: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            {paper.content.sections.find((s) => s.id === cs.sectionId)?.title}
                          </Typography>
                          <Typography variant="body2">{cs.summary}</Typography>
                        </Box>
                      ))}
                    </>
                  )}
                </>
              )}
            </Box>
          )}

          {/* Chat Tab */}
          {sidebarTab === 3 && (
            <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <Box sx={{ flexGrow: 1, overflow: 'auto', p: 1 }}>
                {chatMessages.map((msg, i) => (
                  <Box
                    key={i}
                    sx={{
                      mb: 1,
                      p: 1,
                      bgcolor: msg.role === 'user' ? 'primary.light' : 'grey.100',
                      borderRadius: 1,
                    }}
                  >
                    <Typography variant="body2">{msg.content}</Typography>
                  </Box>
                ))}
                {loadingChat && <CircularProgress size={20} />}
              </Box>
              <Box sx={{ display: 'flex', gap: 1, p: 1 }}>
                <TextField
                  size="small"
                  fullWidth
                  placeholder="Ask about this paper..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendChat()}
                />
                <Button variant="contained" onClick={handleSendChat} disabled={loadingChat}>
                  Send
                </Button>
              </Box>
            </Box>
          )}
        </Box>
      </Drawer>

      {/* View Style Settings Dialog */}
      <ViewStyleSettings open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </Box>
  );
}
