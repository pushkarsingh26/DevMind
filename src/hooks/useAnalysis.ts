import { useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import type { AnalysisDataContextType } from '../context/AnalysisContext';

export const useAnalysis = (): AnalysisDataContextType => {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
};
