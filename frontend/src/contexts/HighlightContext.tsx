import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react';
import type { Highlight, HighlightColorPreset } from '../types';
import { highlightService, presetService } from '../services/api';

interface HighlightContextType {
  highlights: Highlight[];
  presets: HighlightColorPreset[];
  selectedColor: string;
  defaultPreset: HighlightColorPreset | null;
  loadHighlights: (paperId: string) => Promise<void>;
  addHighlight: (paperId: string, highlight: Omit<Highlight, 'id' | 'paperId' | 'createdAt'>) => Promise<Highlight>;
  updateHighlight: (paperId: string, highlightId: string, updates: { color?: string; note?: string }) => Promise<void>;
  removeHighlight: (paperId: string, highlightId: string) => Promise<void>;
  setSelectedColor: (color: string) => void;
  loadPresets: () => Promise<void>;
  createPreset: (name: string, color: string) => Promise<void>;
  setDefaultPreset: (id: string) => Promise<void>;
}

const HighlightContext = createContext<HighlightContextType | undefined>(undefined);

export function HighlightProvider({ children }: { children: ReactNode }) {
  const [highlights, setHighlights] = useState<Highlight[]>([]);
  const [presets, setPresets] = useState<HighlightColorPreset[]>([]);
  const [selectedColor, setSelectedColor] = useState('#FFEB3B');

  const defaultPreset = presets.find((p) => p.isDefault) || null;

  useEffect(() => {
    if (defaultPreset) {
      setSelectedColor(defaultPreset.color);
    }
  }, [defaultPreset]);

  const loadHighlights = useCallback(async (paperId: string) => {
    try {
      const data = await highlightService.getHighlights(paperId);
      setHighlights(data);
    } catch (error) {
      console.error('Failed to load highlights:', error);
    }
  }, []);

  const addHighlight = useCallback(async (paperId: string, highlight: Omit<Highlight, 'id' | 'paperId' | 'createdAt'>) => {
    const created = await highlightService.createHighlight(paperId, highlight);
    setHighlights((prev) => [...prev, created]);
    return created;
  }, []);

  const updateHighlight = useCallback(async (paperId: string, highlightId: string, updates: { color?: string; note?: string }) => {
    const updated = await highlightService.updateHighlight(paperId, highlightId, updates);
    setHighlights((prev) => prev.map((h) => (h.id === highlightId ? updated : h)));
  }, []);

  const removeHighlight = useCallback(async (paperId: string, highlightId: string) => {
    await highlightService.deleteHighlight(paperId, highlightId);
    setHighlights((prev) => prev.filter((h) => h.id !== highlightId));
  }, []);

  const loadPresets = useCallback(async () => {
    try {
      const data = await presetService.getPresets();
      setPresets(data);
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  }, []);

  const createPreset = useCallback(async (name: string, color: string) => {
    const created = await presetService.createPreset(name, color);
    setPresets((prev) => [...prev, created]);
  }, []);

  const setDefaultPreset = useCallback(async (id: string) => {
    const updated = await presetService.setDefault(id);
    setPresets((prev) => prev.map((p) => ({ ...p, isDefault: p.id === id })));
    setSelectedColor(updated.color);
  }, []);

  return (
    <HighlightContext.Provider
      value={{
        highlights,
        presets,
        selectedColor,
        defaultPreset,
        loadHighlights,
        addHighlight,
        updateHighlight,
        removeHighlight,
        setSelectedColor,
        loadPresets,
        createPreset,
        setDefaultPreset,
      }}
    >
      {children}
    </HighlightContext.Provider>
  );
}

export function useHighlight() {
  const context = useContext(HighlightContext);
  if (!context) {
    throw new Error('useHighlight must be used within a HighlightProvider');
  }
  return context;
}
