import React, { useState } from 'react';
import { GitBranch, Archive, Upload, FileText, X } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';
import { motion, AnimatePresence } from 'framer-motion';
import { Card } from './ui';

export const RepositoryCard: React.FC = () => {
  const {
    repositoryURL,
    setRepositoryURL,
    uploadedFile,
    setUploadedFile,
    isAnalyzing,
  } = useAnalysis();

  const [activeTab, setActiveTab] = useState<'url' | 'zip'>(uploadedFile ? 'zip' : 'url');
  const [isDragging, setIsDragging] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (isAnalyzing) return;
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.zip')) {
        setUploadedFile(file);
      } else {
        alert('Please upload a ZIP repository archive only.');
      }
    }
  };

  const clearFile = () => {
    setUploadedFile(null);
  };

  return (
    <Card id="repository-config-section" variant="soft" className="space-y-5 text-left h-full flex flex-col justify-between">
      <div>
        <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2 mb-4">
          <span className="text-xs bg-cyan-accent/10 text-cyan-accent border border-cyan-accent/20 px-2 py-0.5 rounded-lg font-mono font-bold">01</span>
          <span>TARGET REPOSITORY</span>
        </h2>

        {/* Pill Tabs Selector */}
        <div className="flex bg-[#070b14]/25 p-1 rounded-xl border border-border-primary mb-5">
          <button
            type="button"
            disabled={isAnalyzing}
            onClick={() => {
              setActiveTab('url');
              if (uploadedFile) setUploadedFile(null);
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 text-xs font-mono rounded-lg transition-all duration-200 cursor-pointer select-none
              ${
                activeTab === 'url'
                  ? 'bg-dark-900 border border-border-primary text-cyan-accent font-semibold shadow-sm'
                  : 'text-dark-400 hover:text-dark-200'
              }
              ${isAnalyzing ? 'cursor-not-allowed opacity-50' : ''}
            `}
          >
            <GitBranch className="w-3.5 h-3.5" />
            GITHUB URL
          </button>
          <button
            type="button"
            disabled={isAnalyzing}
            onClick={() => {
              setActiveTab('zip');
              if (repositoryURL) setRepositoryURL('');
            }}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 text-xs font-mono rounded-lg transition-all duration-200 cursor-pointer select-none
              ${
                activeTab === 'zip'
                  ? 'bg-dark-900 border border-border-primary text-cyan-accent font-semibold shadow-sm'
                  : 'text-dark-400 hover:text-dark-200'
              }
              ${isAnalyzing ? 'cursor-not-allowed opacity-50' : ''}
            `}
          >
            <Archive className="w-3.5 h-3.5" />
            ZIP ARCHIVE
          </button>
        </div>

        {/* Tab Panels with simple entrance fade */}
        <AnimatePresence mode="wait">
          {activeTab === 'url' ? (
            <motion.div
              key="url-panel"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
              className="space-y-2.5"
            >
              <label htmlFor="repo-url" className="block text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold">
                Repository Github Link
              </label>
              <div className="relative">
                <input
                  id="repo-url"
                  type="url"
                  placeholder="https://github.com/username/repository"
                  value={repositoryURL}
                  onChange={(e) => setRepositoryURL(e.target.value)}
                  disabled={isAnalyzing}
                  className="w-full bg-[#070b14]/30 dark:bg-[#070b14]/50 border border-border-primary hover:border-dark-700/80 focus:border-cyan-accent focus:ring-1 focus:ring-cyan-accent/20 rounded-xl px-4 py-2.5 text-xs text-dark-100 font-sans focus:outline-none disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
                />
              </div>
              <p className="text-[10px] text-dark-500 font-sans">
                Provide a public Git repository address to clone and index context metadata.
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="zip-panel"
              initial={{ opacity: 0, y: 5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
              className="space-y-2.5"
            >
              <label className="block text-[9px] font-mono text-dark-500 uppercase tracking-widest font-bold">
                Upload Archive
              </label>
              {!uploadedFile ? (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-6 text-center bg-[#070b14]/20 transition-all duration-200
                    ${
                      isDragging
                        ? 'border-cyan-accent/60 bg-cyan-accent/10 shadow-[0_0_15px_rgba(6,182,212,0.05)]'
                        : 'border-border-primary'
                    }
                    ${
                      isAnalyzing
                        ? 'cursor-not-allowed opacity-50'
                        : 'hover:border-cyan-accent/40 cursor-pointer'
                    }
                  `}
                >
                  <input
                    id="zip-upload"
                    type="file"
                    accept=".zip"
                    disabled={isAnalyzing}
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  <label
                    htmlFor="zip-upload"
                    className={`flex flex-col items-center justify-center gap-2 ${
                      isAnalyzing ? 'cursor-not-allowed' : 'cursor-pointer'
                    }`}
                  >
                    <Upload className={`w-7 h-7 transition-colors duration-200 ${isDragging ? 'text-cyan-accent' : 'text-dark-500'}`} />
                    <span className="text-xs text-dark-300 font-sans mt-1">
                      Drag & drop .zip here or <span className="text-cyan-accent hover:underline font-semibold">browse</span>
                    </span>
                    <span className="text-[9px] text-dark-500 font-mono">Max archive file size: 50MB</span>
                  </label>
                </div>
              ) : (
                <div className="flex items-center justify-between bg-[#070b14]/40 border border-border-primary rounded-xl p-4 shadow-inner">
                  <div className="flex items-center gap-3">
                    <div className="bg-purple-accent/10 p-2.5 rounded-lg text-purple-accent border border-purple-accent/25">
                      <FileText className="w-5 h-5" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-sans text-dark-100 font-medium truncate max-w-[200px] sm:max-w-[280px]">
                        {uploadedFile.name}
                      </p>
                      <p className="text-xs font-mono text-dark-500 mt-0.5">
                        {(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>
                  </div>
                  {!isAnalyzing && (
                    <button
                      type="button"
                      onClick={clearFile}
                      className="text-dark-500 hover:text-dark-200 p-1.5 hover:bg-dark-800/60 rounded-lg cursor-pointer transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )}
              <p className="text-[10px] text-dark-500 font-sans">
                ZIP packages are securely unpacked in-memory and deleted immediately post-session.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Card>
  );
};
