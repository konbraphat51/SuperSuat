import axios from 'axios';
import type { Paper, PaperDetail, PaperFilter, Translation, Summary, Highlight, HighlightColorPreset } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Paper API
export const paperService = {
  async getPapers(filter: PaperFilter = {}): Promise<{ papers: Paper[]; nextToken?: string }> {
    const params = new URLSearchParams();
    if (filter.pageSize) params.append('pageSize', filter.pageSize.toString());
    if (filter.nextToken) params.append('nextToken', filter.nextToken);
    if (filter.tags?.length) params.append('tags', filter.tags.join(','));
    if (filter.authors?.length) params.append('authors', filter.authors.join(','));

    const response = await apiClient.get(`/papers?${params}`);
    return response.data;
  },

  async getPaper(id: string): Promise<PaperDetail> {
    const response = await apiClient.get(`/papers/${id}`);
    return response.data;
  },

  async uploadPaper(file: File): Promise<Paper> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/papers', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async updatePaper(id: string, updates: Partial<Paper>): Promise<Paper> {
    const response = await apiClient.put(`/papers/${id}`, updates);
    return response.data;
  },
};

// Translation API
export const translationService = {
  async getAvailableLanguages(paperId: string): Promise<string[]> {
    const response = await apiClient.get(`/papers/${paperId}/translations/languages`);
    return response.data.languages;
  },

  async getTranslation(paperId: string, language: string): Promise<Translation> {
    const response = await apiClient.get(`/papers/${paperId}/translations/${language}`);
    return response.data;
  },

  async createTranslation(paperId: string, language: string): Promise<Translation> {
    const response = await apiClient.post(`/papers/${paperId}/translations`, { language });
    return response.data;
  },
};

// Summary API
export const summaryService = {
  async getSummary(paperId: string, language: string): Promise<Summary> {
    const response = await apiClient.get(`/papers/${paperId}/summaries/${language}`);
    return response.data;
  },

  async createSummary(paperId: string, language: string, includeChapterSummaries: boolean): Promise<Summary> {
    const response = await apiClient.post(`/papers/${paperId}/summaries`, {
      language,
      includeChapterSummaries,
    });
    return response.data;
  },
};

// Highlight API
export const highlightService = {
  async getHighlights(paperId: string): Promise<Highlight[]> {
    const response = await apiClient.get(`/papers/${paperId}/highlights`);
    return response.data.highlights;
  },

  async createHighlight(paperId: string, highlight: Omit<Highlight, 'id' | 'paperId' | 'createdAt'>): Promise<Highlight> {
    const response = await apiClient.post(`/papers/${paperId}/highlights`, highlight);
    return response.data;
  },

  async updateHighlight(paperId: string, highlightId: string, updates: { color?: string; note?: string }): Promise<Highlight> {
    const response = await apiClient.put(`/papers/${paperId}/highlights/${highlightId}`, updates);
    return response.data;
  },

  async deleteHighlight(paperId: string, highlightId: string): Promise<void> {
    await apiClient.delete(`/papers/${paperId}/highlights/${highlightId}`);
  },
};

// Highlight Preset API
export const presetService = {
  async getPresets(): Promise<HighlightColorPreset[]> {
    const response = await apiClient.get('/highlight-presets');
    return response.data.presets;
  },

  async createPreset(name: string, color: string): Promise<HighlightColorPreset> {
    const response = await apiClient.post('/highlight-presets', { name, color });
    return response.data;
  },

  async updatePreset(id: string, updates: { name?: string; color?: string }): Promise<HighlightColorPreset> {
    const response = await apiClient.put(`/highlight-presets/${id}`, updates);
    return response.data;
  },

  async deletePreset(id: string): Promise<void> {
    await apiClient.delete(`/highlight-presets/${id}`);
  },

  async setDefault(id: string): Promise<HighlightColorPreset> {
    const response = await apiClient.put(`/highlight-presets/${id}/default`);
    return response.data;
  },
};

// Chat API
export const chatService = {
  async sendMessage(paperId: string, message: string): Promise<string> {
    const response = await apiClient.post(`/papers/${paperId}/chat`, { message });
    return response.data.message;
  },
};
