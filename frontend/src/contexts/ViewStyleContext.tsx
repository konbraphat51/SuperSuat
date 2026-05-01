import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import type { ViewStyle } from '../types';

interface ViewStyleContextType {
  style: ViewStyle;
  updateStyle: (updates: Partial<ViewStyle>) => void;
}

const defaultStyle: ViewStyle = {
  fontSize: 16,
  lineHeight: 1.6,
  fontFamily: 'Georgia, serif',
  colorSet: 'light',
  marginSize: 40,
};

const ViewStyleContext = createContext<ViewStyleContextType | undefined>(undefined);

export function ViewStyleProvider({ children }: { children: ReactNode }) {
  const [style, setStyle] = useState<ViewStyle>(() => {
    const saved = localStorage.getItem('viewStyle');
    return saved ? JSON.parse(saved) : defaultStyle;
  });

  const updateStyle = useCallback((updates: Partial<ViewStyle>) => {
    setStyle((prev) => {
      const newStyle = { ...prev, ...updates };
      localStorage.setItem('viewStyle', JSON.stringify(newStyle));
      return newStyle;
    });
  }, []);

  return (
    <ViewStyleContext.Provider value={{ style, updateStyle }}>
      {children}
    </ViewStyleContext.Provider>
  );
}

export function useViewStyle() {
  const context = useContext(ViewStyleContext);
  if (!context) {
    throw new Error('useViewStyle must be used within a ViewStyleProvider');
  }
  return context;
}
