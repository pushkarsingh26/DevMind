import { useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import type { AnalysisContextType } from '../types';

export const useAnalysis = (): AnalysisContextType => {
  const context = useContext(AnalysisContext);
  if (!context) {
    throw new Error('useAnalysis must be used within an AnalysisProvider');
  }
  return context;
};
