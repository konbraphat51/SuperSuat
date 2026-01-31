import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { PaperList } from '../components/PaperList';
import { ViewStyleProvider } from '../contexts/ViewStyleContext';
import { HighlightProvider } from '../contexts/HighlightContext';

// Mock the API service
vi.mock('../services/api', () => ({
  paperService: {
    getPapers: vi.fn().mockResolvedValue({
      papers: [
        {
          id: '1',
          title: 'Test Paper',
          authors: ['Author 1'],
          description: 'Test description',
          tags: ['AI'],
          createdAt: '2024-01-01T00:00:00Z',
        },
      ],
      nextToken: undefined,
    }),
  },
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>
    <ViewStyleProvider>
      <HighlightProvider>
        {children}
      </HighlightProvider>
    </ViewStyleProvider>
  </BrowserRouter>
);

describe('PaperList', () => {
  it('renders the paper list header', async () => {
    render(
      <TestWrapper>
        <PaperList />
      </TestWrapper>
    );

    expect(screen.getByText('Papers')).toBeInTheDocument();
  });

  it('renders the upload button', async () => {
    render(
      <TestWrapper>
        <PaperList />
      </TestWrapper>
    );

    expect(screen.getByText('Upload Paper')).toBeInTheDocument();
  });
});
