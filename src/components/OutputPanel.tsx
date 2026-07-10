import React, { useState, useContext, useEffect } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Terminal, Clipboard, Check, Download, FileText, ChevronDown, ChevronUp, 
  AlertTriangle, Maximize2, Minimize2, Printer, Zap, Network, ShieldCheck, 
  ThumbsUp, ShieldAlert, Bug, TestTube, Sparkles, Copy
} from 'lucide-react';

export const OutputPanel: React.FC = () => {
  const context = useContext(AnalysisContext);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'structured' | 'markdown'>('structured');
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');
  const [isFullScreen, setIsFullScreen] = useState(false);
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  // Esc key to exit full screen
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isFullScreen) {
        setIsFullScreen(false);
      }
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isFullScreen]);

  // Lock scroll when full screen
  useEffect(() => {
    if (isFullScreen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isFullScreen]);

  if (!context) return null;
  const { analysisResult, parsedReport, selectedTask, addToast } = context;

  const handleCopy = () => {
    if (!analysisResult) return;
    navigator.clipboard.writeText(analysisResult);
    setCopied(true);
    addToast('success', 'Markdown report copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopySnippet = (content: string, key: string) => {
    navigator.clipboard.writeText(content);
    setCopiedCodeId(key);
    addToast('success', 'Snippet copied to clipboard!');
    setTimeout(() => setCopiedCodeId(null), 2000);
  };

  const handleExportMarkdown = () => {
    if (!analysisResult) return;
    const blob = new Blob([analysisResult], { type: 'text/markdown;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const filename = `${parsedReport?.repository?.name || 'devmind'}_${selectedTask}_report.md`;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    addToast('success', 'Markdown report exported successfully!');
  };

  const handleExportPDF = () => {
    addToast('success', 'Opening print preview. For best results, select landscape/portrait scaling.');
    setTimeout(() => {
      window.print();
    }, 500);
  };

  if (!analysisResult) {
    return (
      <div id="reports-output-section" className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-8 text-center shadow-lg transition-all duration-300">
        <div className="flex justify-center mb-3">
          <Terminal className="w-8 h-8 text-dark-600 animate-pulse" />
        </div>
        <p className="text-xs font-mono text-dark-400 max-w-sm mx-auto">
          Audit report awaiting execution. Provide repository details and trigger the scanner pipeline above.
        </p>
      </div>
    );
  }

  const aiOutput = parsedReport?.aiOutput;
  const isFallback = aiOutput?.is_fallback ?? true;

  // Custom Inline Markdown parser
  const parseInlineStyles = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    const matches = text.split(regex);

    matches.forEach((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        parts.push(
          <strong key={i} className="font-bold text-dark-100 font-sans">
            {part.slice(2, -2)}
          </strong>
        );
      } else if (part.startsWith('`') && part.endsWith('`')) {
        parts.push(
          <code key={i} className="bg-dark-950 border border-dark-800/60 rounded px-1.5 py-0.5 text-cyan-400 font-semibold font-mono text-[11px] mx-0.5">
            {part.slice(1, -1)}
          </code>
        );
      } else {
        parts.push(part);
      }
    });

    return parts.length > 0 ? parts : [text];
  };

  const renderMarkdownText = (markdown: string) => {
    const lines = markdown.split('\n');
    const elements: React.ReactNode[] = [];
    let key = 0;
    
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeBlockLang = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          const content = codeBlockContent.join('\n');
          const snippetKey = `code-${key++}`;
          elements.push(
            <div key={snippetKey} className="my-4 bg-dark-950 border border-dark-850 rounded-xl overflow-hidden font-mono shadow-inner">
              <div className="bg-dark-900/60 border-b border-dark-850 px-4 py-2 flex items-center justify-between text-[10px] text-dark-400 font-mono font-bold tracking-wider">
                <span>{codeBlockLang.toUpperCase() || 'CODE'} SNIPPET</span>
                <button
                  onClick={() => handleCopySnippet(content, snippetKey)}
                  className="text-dark-500 hover:text-cyan-400 flex items-center gap-1.5 transition-colors cursor-pointer"
                >
                  {copiedCodeId === snippetKey ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" />
                      <span className="text-emerald-400 text-[9px]">COPIED</span>
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      <span className="text-[9px]">COPY</span>
                    </>
                  )}
                </button>
              </div>
              <pre className="p-4 overflow-x-auto text-[11px] text-cyan-300/90 leading-relaxed font-mono">
                <code>{content}</code>
              </pre>
            </div>
          );
          codeBlockContent = [];
          inCodeBlock = false;
        } else {
          codeBlockLang = line.replace('```', '').trim();
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      if (line.trim() === '---') {
        elements.push(<hr key={`hr-${key++}`} className="my-5 border-dark-850/60" />);
        continue;
      }

      if (line.startsWith('# ')) {
        elements.push(
          <h2 key={`h1-${key++}`} className="text-base font-bold text-dark-50 tracking-tight font-display mt-6 mb-3 border-b border-dark-850/50 pb-2">
            {parseInlineStyles(line.substring(2))}
          </h2>
        );
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h3 key={`h2-${key++}`} className="text-sm font-semibold text-dark-100 font-display mt-5 mb-2.5">
            {parseInlineStyles(line.substring(3))}
          </h3>
        );
        continue;
      }
      if (line.startsWith('### ')) {
        elements.push(
          <h4 key={`h3-${key++}`} className="text-xs font-semibold text-dark-300 font-display mt-4 mb-2">
            {parseInlineStyles(line.substring(4))}
          </h4>
        );
        continue;
      }

      if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <ul key={`ul-${key++}`} className="list-disc pl-5 my-1.5 font-sans text-xs text-dark-300 leading-relaxed">
            <li>{parseInlineStyles(line.substring(2))}</li>
          </ul>
        );
        continue;
      }
      if (/^\d+\.\s/.test(line)) {
        const content = line.replace(/^\d+\.\s/, '');
        elements.push(
          <ol key={`ol-${key++}`} className="list-decimal pl-5 my-1.5 font-sans text-xs text-dark-300 leading-relaxed">
            <li>{parseInlineStyles(content)}</li>
          </ol>
        );
        continue;
      }

      if (line.trim() === '') {
        continue;
      }

      elements.push(
        <p key={`p-${key++}`} className="my-2.5 text-xs text-dark-300 font-sans leading-relaxed">
          {parseInlineStyles(line)}
        </p>
      );
    }

    return elements;
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  const renderItemSection = (title: string, id: string, items?: string[], content?: string, icon?: React.ReactNode) => {
    const isExpanded = expandedSection === id;
    if (!items && !content) return null;

    return (
      <div className="border border-dark-850 rounded-xl overflow-hidden bg-[#070b14]/30 hover:border-dark-800 transition-all duration-200">
        <button
          onClick={() => toggleSection(id)}
          className="w-full flex items-center justify-between p-4.5 bg-dark-900/40 hover:bg-dark-900/80 font-display text-sm font-semibold text-dark-200 cursor-pointer text-left transition-all"
        >
          <span className="flex items-center gap-2.5">
            {icon || <FileText className="w-4 h-4 text-cyan-400" />}
            <span className="tracking-wide uppercase text-xs">{title}</span>
          </span>
          {isExpanded ? <ChevronUp className="w-4 h-4 text-cyan-400" /> : <ChevronDown className="w-4 h-4 text-dark-400" />}
        </button>
        
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: 'easeInOut' }}
              style={{ overflow: 'hidden' }}
            >
              <div className="p-5 border-t border-dark-850/60 bg-[#070b14]/50 space-y-3.5">
                {content && <p className="text-xs text-dark-300 font-sans leading-relaxed">{content}</p>}
                {items && items.length > 0 && (
                  <ul className="list-disc pl-5 font-sans text-xs text-dark-300 space-y-2.5">
                    {items.map((item, idx) => (
                      <li key={idx} className="leading-relaxed">{parseInlineStyles(item)}</li>
                    ))}
                  </ul>
                )}
                {items && items.length === 0 && !content && (
                  <p className="text-xs font-mono text-dark-500 italic">No telemetry metrics recorded for this audit scope.</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  const ContentBody = () => (
    <>
      {activeTab === 'markdown' || isFallback ? (
        <div className="overflow-y-auto pr-2 print:max-h-none print:pr-0 leading-relaxed">
          {isFallback && (
            <div className="border border-amber-500/20 bg-amber-950/10 rounded-xl p-4.5 mb-5 text-amber-300 font-mono text-xs flex items-start gap-3">
              <AlertTriangle className="w-4.5 h-4.5 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <p className="font-bold uppercase tracking-wider text-[11px]">Fallback Analyzer Active</p>
                <p className="mt-1 text-dark-400 leading-normal">
                  The primary AI reasoning core is offline. Rendered metrics show local static heuristic parsing.
                </p>
              </div>
            </div>
          )}
          <div className="space-y-1">{renderMarkdownText(analysisResult)}</div>
        </div>
      ) : (
        <div className="space-y-4 font-sans text-xs">
          {/* 1. Executive Summary */}
          {renderItemSection('Executive Summary', 'summary', undefined, aiOutput?.executive_summary, <Zap className="w-4 h-4 text-amber-400" />)}

          {/* 2. Architecture & Structure */}
          {(selectedTask === 'explain' || aiOutput?.high_level_architecture || aiOutput?.entry_points || aiOutput?.important_modules || aiOutput?.data_flow) && (
            <div className="border border-dark-850 rounded-xl overflow-hidden bg-[#070b14]/30 hover:border-dark-800 transition-all duration-200">
              <button
                onClick={() => toggleSection('architecture')}
                className="w-full flex items-center justify-between p-4.5 bg-dark-900/40 hover:bg-dark-900/85 font-display text-sm font-semibold text-dark-200 cursor-pointer text-left transition-all"
              >
                <span className="flex items-center gap-2.5">
                  <Network className="w-4 h-4 text-cyan-400" />
                  <span className="tracking-wide uppercase text-xs">Structure & Code Architecture</span>
                </span>
                {expandedSection === 'architecture' ? <ChevronUp className="w-4 h-4 text-cyan-400" /> : <ChevronDown className="w-4 h-4 text-dark-400" />}
              </button>
              
              <AnimatePresence initial={false}>
                {expandedSection === 'architecture' && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                  >
                    <div className="p-5 border-t border-dark-850/60 bg-[#070b14]/50 space-y-4">
                      {aiOutput?.high_level_architecture && aiOutput.high_level_architecture.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">High-Level Layers:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300 font-sans">
                            {aiOutput.high_level_architecture.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.entry_points && aiOutput.entry_points.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Entry Points:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300 font-sans">
                            {aiOutput.entry_points.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.important_modules && aiOutput.important_modules.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Primary Modules:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300 font-sans">
                            {aiOutput.important_modules.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.data_flow && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Data Flow Description:</h4>
                          <p className="text-dark-300 leading-relaxed font-sans">{aiOutput.data_flow}</p>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* 3. Strengths */}
          {renderItemSection('Key Strengths', 'strengths', aiOutput?.strengths, undefined, <ShieldCheck className="w-4 h-4 text-emerald-400" />)}

          {/* 4. Improvements */}
          {renderItemSection('Improvements & Weaknesses', 'improvements', aiOutput?.improvements || aiOutput?.risk_areas, undefined, <ThumbsUp className="w-4 h-4 text-purple-400" />)}

          {/* 5. Recommendations */}
          {renderItemSection('Actionable Recommendations', 'recommendations', aiOutput?.recommendations, undefined, <Sparkles className="w-4 h-4 text-cyan-400" />)}

          {/* 6. Security Observations */}
          {renderItemSection('Security Observations', 'security', aiOutput?.security_observations, undefined, <ShieldAlert className="w-4 h-4 text-rose-400" />)}

          {/* 7. Performance Observations */}
          {renderItemSection('Performance Observations', 'performance', aiOutput?.performance_observations || aiOutput?.performance_concerns, undefined, <Zap className="w-4 h-4 text-amber-400" />)}

          {/* 8. Testing Recommendations */}
          {(selectedTask === 'tests' || aiOutput?.unit_test_suggestions || aiOutput?.integration_test_suggestions || aiOutput?.coverage_status || aiOutput?.mock_opportunities) && (
            <div className="border border-dark-850 rounded-xl overflow-hidden bg-[#070b14]/30 hover:border-dark-800 transition-all duration-200">
              <button
                onClick={() => toggleSection('testing')}
                className="w-full flex items-center justify-between p-4.5 bg-dark-900/40 hover:bg-dark-900/85 font-display text-sm font-semibold text-dark-200 cursor-pointer text-left transition-all"
              >
                <span className="flex items-center gap-2.5">
                  <TestTube className="w-4 h-4 text-purple-400" />
                  <span className="tracking-wide uppercase text-xs">Testing Recommendations</span>
                </span>
                {expandedSection === 'testing' ? <ChevronUp className="w-4 h-4 text-cyan-400" /> : <ChevronDown className="w-4 h-4 text-dark-400" />}
              </button>
              
              <AnimatePresence initial={false}>
                {expandedSection === 'testing' && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                  >
                    <div className="p-5 border-t border-dark-850/60 bg-[#070b14]/50 space-y-4">
                      {aiOutput?.unit_test_suggestions && aiOutput.unit_test_suggestions.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Unit Tests:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.unit_test_suggestions.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.integration_test_suggestions && aiOutput.integration_test_suggestions.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Integration Tests:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.integration_test_suggestions.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.mock_opportunities && aiOutput.mock_opportunities.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Mock Targets:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.mock_opportunities.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.coverage_status && aiOutput.coverage_status.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Coverage Gap Areas:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.coverage_status.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* 9. Bug Finder Observations */}
          {(selectedTask === 'bugs' || aiOutput?.logical_issues || aiOutput?.error_prone_patterns || aiOutput?.null_handling_concerns || aiOutput?.async_concerns || aiOutput?.resource_management_observations) && (
            <div className="border border-dark-850 rounded-xl overflow-hidden bg-[#070b14]/30 hover:border-dark-800 transition-all duration-200">
              <button
                onClick={() => toggleSection('bugs')}
                className="w-full flex items-center justify-between p-4.5 bg-dark-900/40 hover:bg-dark-900/85 font-display text-sm font-semibold text-dark-200 cursor-pointer text-left transition-all"
              >
                <span className="flex items-center gap-2.5">
                  <Bug className="w-4 h-4 text-rose-400" />
                  <span className="tracking-wide uppercase text-xs">Potential Bugs & Defects</span>
                </span>
                {expandedSection === 'bugs' ? <ChevronUp className="w-4 h-4 text-cyan-400" /> : <ChevronDown className="w-4 h-4 text-dark-400" />}
              </button>
              
              <AnimatePresence initial={false}>
                {expandedSection === 'bugs' && (
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 'auto' }}
                    exit={{ height: 0 }}
                    transition={{ duration: 0.2, ease: 'easeOut' }}
                  >
                    <div className="p-5 border-t border-dark-850/60 bg-[#070b14]/50 space-y-4">
                      {aiOutput?.logical_issues && aiOutput.logical_issues.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Logical Flaws:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.logical_issues.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.error_prone_patterns && aiOutput.error_prone_patterns.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Error Prone Patterns:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.error_prone_patterns.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.null_handling_concerns && aiOutput.null_handling_concerns.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Null Handling Issues:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.null_handling_concerns.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.async_concerns && aiOutput.async_concerns.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Async / Flow Concerns:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.async_concerns.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                      {aiOutput?.resource_management_observations && aiOutput.resource_management_observations.length > 0 && (
                        <div>
                          <h4 className="text-dark-400 font-bold uppercase tracking-wider mb-2 text-[9px] font-mono">Resource Leaks / Management:</h4>
                          <ul className="list-disc pl-5 space-y-2 text-dark-300">
                            {aiOutput.resource_management_observations.map((item, i) => <li key={i} className="leading-relaxed">{parseInlineStyles(item)}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>
      )}
    </>
  );

  return (
    <>
      <div id="reports-output-section" className="bg-[#0f172a]/60 backdrop-blur-xl border border-dark-800/80 rounded-2xl p-6 shadow-xl space-y-5 print:border-none print:bg-white print:text-black">
        {/* Action Panel Bar */}
        <div className="sticky top-0 z-20 bg-[#0f172a]/95 backdrop-blur-md pb-4 mb-4 border-b border-dark-850 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 print:hidden">
          <h2 className="text-base font-bold text-dark-100 font-display flex items-center gap-2">
            <span className="text-xs bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-lg font-mono">07</span>
            <span>PIPELINE OUTPUT AUDIT REPORT</span>
          </h2>

          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            {/* View Switchers */}
            <div className="flex border border-dark-850 rounded-xl bg-[#070b14] p-1 text-xs font-mono">
              <button
                onClick={() => setActiveTab('structured')}
                className={`px-3 py-1.5 rounded-lg cursor-pointer transition-colors ${activeTab === 'structured' ? 'bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20 shadow-md' : 'text-dark-400 hover:text-dark-200'}`}
              >
                INTERACTIVE
              </button>
              <button
                onClick={() => setActiveTab('markdown')}
                className={`px-3 py-1.5 rounded-lg cursor-pointer transition-colors ${activeTab === 'markdown' ? 'bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20 shadow-md' : 'text-dark-400 hover:text-dark-200'}`}
              >
                RAW MD
              </button>
            </div>

            {/* Maximise / Reading mode button */}
            <button
              onClick={() => setIsFullScreen(true)}
              className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-3 py-2 rounded-xl bg-[#070b14] cursor-pointer transition-all"
              title="Enter full-screen reading mode"
            >
              <Maximize2 className="w-3.5 h-3.5" />
              <span className="hidden md:inline">EXPAND</span>
            </button>

            {/* Copy Report */}
            <button
              onClick={handleCopy}
              className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-3 py-2 rounded-xl bg-[#070b14] cursor-pointer transition-all"
              title="Copy markdown content"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Clipboard className="w-3.5 h-3.5" />}
              <span className="hidden md:inline">COPY</span>
            </button>

            {/* Export MD */}
            <button
              onClick={handleExportMarkdown}
              className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-3 py-2 rounded-xl bg-[#070b14] cursor-pointer transition-all"
              title="Download report file (.md)"
            >
              <Download className="w-3.5 h-3.5" />
              <span className="hidden md:inline">EXPORT MD</span>
            </button>

            {/* Print PDF */}
            <button
              onClick={handleExportPDF}
              className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-3 py-2 rounded-xl bg-[#070b14] cursor-pointer transition-all"
              title="Open printer interface"
            >
              <Printer className="w-3.5 h-3.5" />
              <span className="hidden md:inline">PRINT</span>
            </button>
          </div>
        </div>

        {/* Local Printable header */}
        <div className="hidden print:block mb-6 font-mono text-black">
          <h1 className="text-xl font-bold border-b-2 border-black pb-2 uppercase">DevMind Code Intelligence Audit Report</h1>
          <p className="text-xs mt-2 text-gray-700">
            Scanned on {new Date().toLocaleString()} for {parsedReport?.repository?.owner}/{parsedReport?.repository?.name}
          </p>
        </div>

        {/* Main report viewer body */}
        <div className="print:block max-h-[600px] overflow-y-auto pr-1">
          <ContentBody />
        </div>
      </div>

      {/* Full-Screen Reading Mode Portal overlay */}
      <AnimatePresence>
        {isFullScreen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#070b14]/98 backdrop-blur-md flex flex-col overflow-hidden"
          >
            {/* Header bar */}
            <div className="bg-[#0f172a]/70 border-b border-dark-800 px-6 py-4 flex items-center justify-between shadow-md shrink-0">
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono font-bold text-cyan-400 border border-cyan-500/20 px-2 py-0.5 rounded-lg bg-cyan-950/20 uppercase tracking-widest">
                  READING MODE
                </span>
                <span className="text-sm font-semibold text-dark-100 font-display">
                  {parsedReport?.repository?.owner}/{parsedReport?.repository?.name} — {selectedTask?.toUpperCase()} AUDIT
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-3 py-1.5 rounded-xl bg-[#070b14] cursor-pointer transition-all"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Clipboard className="w-3.5 h-3.5" />}
                  <span>COPY</span>
                </button>
                <button
                  onClick={() => setIsFullScreen(false)}
                  className="flex items-center gap-1.5 text-xs font-mono text-dark-300 hover:text-rose-400 border border-dark-800 hover:border-rose-900/30 px-3 py-1.5 rounded-xl bg-[#070b14] cursor-pointer transition-all"
                >
                  <Minimize2 className="w-3.5 h-3.5" />
                  <span>CLOSE</span>
                </button>
              </div>
            </div>

            {/* centered highly-readable reading viewport */}
            <div className="flex-1 overflow-y-auto px-6 py-10">
              <div className="max-w-4xl mx-auto w-full space-y-6">
                <div className="flex justify-center border-b border-dark-850/60 pb-4 mb-4">
                  <div className="flex border border-dark-850 rounded-xl bg-[#070b14] p-1 text-xs font-mono">
                    <button
                      onClick={() => setActiveTab('structured')}
                      className={`px-4 py-1.5 rounded-lg cursor-pointer transition-colors ${activeTab === 'structured' ? 'bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20' : 'text-dark-400 hover:text-dark-200'}`}
                    >
                      INTERACTIVE DOCUMENTATION
                    </button>
                    <button
                      onClick={() => setActiveTab('markdown')}
                      className={`px-4 py-1.5 rounded-lg cursor-pointer transition-colors ${activeTab === 'markdown' ? 'bg-cyan-500/15 text-cyan-400 font-bold border border-cyan-500/20' : 'text-dark-400 hover:text-dark-200'}`}
                    >
                      RAW MARKDOWN SOURCE
                    </button>
                  </div>
                </div>
                <ContentBody />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};
