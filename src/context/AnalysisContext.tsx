  import React, { createContext, useState, useEffect, useRef, useCallback } from 'react';
  import type { TaskType, MultiAgentStatus, AnalysisContextType } from '../types';
  import * as api from '../services/api';

  export const AnalysisContext = createContext<AnalysisContextType | undefined>(undefined);

  const initialStatus: MultiAgentStatus = {
    planner: { status: 'waiting', message: 'Waiting...' },
    retriever: { status: 'waiting', message: 'Waiting...' },
    reviewer: { status: 'waiting', message: 'Waiting...' },
    critic: { status: 'waiting', message: 'Waiting...' },
  };

  export const AnalysisProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [status, setStatus] = useState<MultiAgentStatus>(initialStatus);
    const [selectedTask, setSelectedTaskState] = useState<TaskType>('review');
    const [repositoryURL, setRepositoryURLState] = useState<string>('');
    const [uploadedFile, setUploadedFileState] = useState<File | null>(null);
    const [analysisResult, setAnalysisResult] = useState<string | null>(null);
    const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);

    const pollingIntervalRef = useRef<number | null>(null);
    const currentTaskIdRef = useRef<string | null>(null);

    // Clear polling on unmount
    useEffect(() => {
      return () => {
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current);
        }
      };
    }, []);

    const setSelectedTask = useCallback((task: TaskType) => {
      setSelectedTaskState(task);
    }, []);

    const setRepositoryURL = useCallback((url: string) => {
      setRepositoryURLState(url);
      setUploadedFileState(null); // Clear uploaded file if URL is set
    }, []);

    const setUploadedFile = useCallback((file: File | null) => {
      setUploadedFileState(file);
      if (file) {
        setRepositoryURLState(''); // Clear URL if file is uploaded
      }
    }, []);

    const resetAnalysis = useCallback(() => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
      currentTaskIdRef.current = null;
      setStatus(initialStatus);
      setAnalysisResult(null);
      setIsAnalyzing(false);
    }, []);

    const startAnalysis = useCallback(async () => {
      if (!repositoryURL && !uploadedFile) {
        alert('Please provide either a GitHub Repository URL or upload a ZIP file.');
        return;
      }

      // Reset old execution states
      resetAnalysis();
      setIsAnalyzing(true);

      try {
        let response: { taskId: string };

        // Select appropriate endpoint depending on input type
        if (uploadedFile) {
          response = await api.uploadRepository(uploadedFile, selectedTask);
        } else {
          response = await api.reviewRepository(repositoryURL, selectedTask);
        }

        currentTaskIdRef.current = response.taskId;

        // Immediately run first status scan
        const firstScan = await api.getStatus(response.taskId);
        setStatus(firstScan.status);

        // Start interval polling
        pollingIntervalRef.current = window.setInterval(async () => {
          if (!currentTaskIdRef.current) return;

          try {
            const scan = await api.getStatus(currentTaskIdRef.current);
            setStatus(scan.status);

            if (scan.isDone) {
              setAnalysisResult(scan.resultText);
              setIsAnalyzing(false);
              if (pollingIntervalRef.current) {
                clearInterval(pollingIntervalRef.current);
                pollingIntervalRef.current = null;
              }
            }
          } catch (pollError) {
            console.error('Error polling agent status:', pollError);
            setIsAnalyzing(false);
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current);
              pollingIntervalRef.current = null;
            }
          }
        }, 1000);

      } catch (err) {
        console.error('Failed to trigger analysis:', err);
        setIsAnalyzing(false);
        alert('Failed to start analysis. Check console log for details.');
      }
    }, [repositoryURL, uploadedFile, selectedTask, resetAnalysis]);

    return (
      <AnalysisContext.Provider
        value={{
          status,
          selectedTask,
          repositoryURL,
          uploadedFile,
          analysisResult,
          isAnalyzing,
          setSelectedTask,
          setRepositoryURL,
          setUploadedFile,
          startAnalysis,
          resetAnalysis,
        }}
      >
        {children}
      </AnalysisContext.Provider>
    );
  };
