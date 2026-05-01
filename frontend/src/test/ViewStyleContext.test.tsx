import { describe, it, expect } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { ViewStyleProvider, useViewStyle } from '../contexts/ViewStyleContext';

describe('ViewStyleContext', () => {
  it('provides default style values', () => {
    const { result } = renderHook(() => useViewStyle(), {
      wrapper: ViewStyleProvider,
    });

    expect(result.current.style.fontSize).toBe(16);
    expect(result.current.style.lineHeight).toBe(1.6);
    expect(result.current.style.colorSet).toBe('light');
  });

  it('updates style values', () => {
    const { result } = renderHook(() => useViewStyle(), {
      wrapper: ViewStyleProvider,
    });

    act(() => {
      result.current.updateStyle({ fontSize: 20 });
    });

    expect(result.current.style.fontSize).toBe(20);
  });

  it('updates multiple style properties', () => {
    const { result } = renderHook(() => useViewStyle(), {
      wrapper: ViewStyleProvider,
    });

    act(() => {
      result.current.updateStyle({
        fontSize: 18,
        colorSet: 'dark',
        lineHeight: 2.0,
      });
    });

    expect(result.current.style.fontSize).toBe(18);
    expect(result.current.style.colorSet).toBe('dark');
    expect(result.current.style.lineHeight).toBe(2.0);
  });
});
