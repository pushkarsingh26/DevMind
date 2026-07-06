import React, { useState } from 'react';
import { GitBranch, Archive, Upload, FileText, X } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';

export const RepositoryCard: React.FC = () => {
  const {
    repositoryURL,
    setRepositoryURL,
    uploadedFile,
    setUploadedFile,
    isAnalyzing,
  } = useAnalysis();

  const [activeTab, setActiveTab] = useState<'url' | 'zip'>(uploadedFile ? 'zip' : 'url');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      setUploadedFile(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
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
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6">
      <h2 className="text-base font-semibold text-dark-100 font-mono mb-4 flex items-center gap-2">
        <span>01.</span> TARGET REPOSITORY
      </h2>

      {/* Tabs */}
      <div className="flex bg-dark-950 p-1 rounded-md border border-dark-800 mb-6">
        <button
          type="button"
          disabled={isAnalyzing}
          onClick={() => {
            setActiveTab('url');
            if (uploadedFile) setUploadedFile(null);
          }}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 text-xs font-mono rounded cursor-pointer
            ${
              activeTab === 'url'
                ? 'bg-dark-800 text-brand-400 border border-dark-700 font-semibold'
                : 'text-dark-400 hover:text-dark-200'
            }
            ${isAnalyzing ? 'cursor-not-allowed opacity-50' : ''}
          `}
        >
          <GitBranch className="w-4 h-4" />
          GITHUB URL
        </button>
        <button
          type="button"
          disabled={isAnalyzing}
          onClick={() => {
            setActiveTab('zip');
            if (repositoryURL) setRepositoryURL('');
          }}
          className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 text-xs font-mono rounded cursor-pointer
            ${
              activeTab === 'zip'
                ? 'bg-dark-800 text-brand-400 border border-dark-700 font-semibold'
                : 'text-dark-400 hover:text-dark-200'
            }
            ${isAnalyzing ? 'cursor-not-allowed opacity-50' : ''}
          `}
        >
          <Archive className="w-4 h-4" />
          ZIP ARCHIVE
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'url' ? (
        <div>
          <label htmlFor="repo-url" className="block text-xs font-mono text-dark-400 mb-2">
            REPOSITORY URL
          </label>
          <div className="relative">
            <input
              id="repo-url"
              type="url"
              placeholder="https://github.com/username/repository"
              value={repositoryURL}
              onChange={(e) => setRepositoryURL(e.target.value)}
              disabled={isAnalyzing}
              className="w-full bg-dark-950 border border-dark-800 rounded px-4 py-3 text-sm text-dark-100 font-mono placeholder-dark-600 focus:outline-none focus:border-brand-500 disabled:opacity-50"
            />
          </div>
          <p className="text-[11px] text-dark-500 font-mono mt-2">
            Provide a public repository address to retrieve index metadata.
          </p>
        </div>
      ) : (
        <div>
          <label className="block text-xs font-mono text-dark-400 mb-2">
            UPLOAD ARCHIVE
          </label>
          {!uploadedFile ? (
            <div
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              className={`border-2 border-dashed rounded-lg p-6 text-center bg-dark-950
                ${
                  isAnalyzing
                    ? 'border-dark-800 cursor-not-allowed opacity-50'
                    : 'border-dark-800 hover:border-brand-500/50 cursor-pointer'
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
                <Upload className="w-8 h-8 text-dark-500" />
                <span className="text-sm font-mono text-dark-300">
                  Drag & drop .zip here or <span className="text-brand-400">browse</span>
                </span>
                <span className="text-xs text-dark-600 font-mono">Max size: 50MB</span>
              </label>
            </div>
          ) : (
            <div className="flex items-center justify-between bg-dark-950 border border-dark-800 rounded p-4">
              <div className="flex items-center gap-3">
                <div className="bg-brand-600/10 p-2 rounded text-brand-400 border border-brand-500/10">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-mono text-dark-200 truncate max-w-[200px] sm:max-w-[250px]">
                    {uploadedFile.name}
                  </p>
                  <p className="text-xs font-mono text-dark-500">
                    {(uploadedFile.size / (1024 * 1024)).toFixed(2)} MB
                  </p>
                </div>
              </div>
              {!isAnalyzing && (
                <button
                  type="button"
                  onClick={clearFile}
                  className="text-dark-500 hover:text-dark-300 p-1 hover:bg-dark-800 rounded cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
          <p className="text-[11px] text-dark-500 font-mono mt-2">
            ZIP packages are securely unpacked in-memory and deleted post-session.
          </p>
        </div>
      )}
    </div>
  );
};
