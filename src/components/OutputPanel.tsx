import React, { useState, useContext } from 'react';
import { AnalysisContext } from '../context/AnalysisContext';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Terminal, Clipboard, Check, Download, FileText, ChevronDown, ChevronUp, 
  AlertTriangle
} from 'lucide-react';

export const OutputPanel: React.FC = () => {
  const context = useContext(AnalysisContext);
  if (!context) return null;

  const { analysisResult, parsedReport, selectedTask, addToast } = context;
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'structured' | 'markdown'>('structured');
  const [expandedSection, setExpandedSection] = useState<string | null>('summary');

  const handleCopy = () => {
    if (!analysisResult) return;
    navigator.clipboard.writeText(analysisResult);
    setCopied(true);
    addToast('success', 'Markdown report copied to clipboard!');
    setTimeout(() => setCopied(false), 2000);
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
    addToast('success', 'Opening PDF printer dialog. Optimize layout using print settings.');
    setTimeout(() => {
      window.print();
    }, 500);
  };

  if (!analysisResult) {
    return (
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-8 text-center print:hidden">
        <div className="flex justify-center mb-3">
          <Terminal className="w-8 h-8 text-dark-700" />
        </div>
        <p className="text-sm font-mono text-dark-500">
          No analysis yet. Fill in target repository and start the pipeline.
        </p>
      </div>
    );
  }

  const aiOutput = parsedReport?.aiOutput;
  const isFallback = aiOutput?.is_fallback ?? true;

  // Custom Inline Markdown parser for text inside lists/paragraphs
  const parseInlineStyles = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    const regex = /(\*\*.*?\*\*|`.*?`)/g;
    const matches = text.split(regex);

    matches.forEach((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        parts.push(
          <strong key={i} className="font-semibold text-dark-100">
            {part.slice(2, -2)}
          </strong>
        );
      } else if (part.startsWith('`') && part.endsWith('`')) {
        parts.push(
          <code key={i} className="bg-dark-950 border border-dark-800 rounded px-1.5 py-0.5 text-brand-400 font-semibold mx-0.5">
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
          elements.push(
            <div key={`code-${key++}`} className="my-4 bg-dark-950 border border-dark-850 rounded-md overflow-hidden font-mono">
              {codeBlockLang && (
                <div className="bg-dark-900 border-b border-dark-850 px-4 py-2 flex items-center justify-between text-[11px] text-dark-400">
                  <span>{codeBlockLang.toUpperCase()} CODE</span>
                </div>
              )}
              <pre className="p-4 overflow-x-auto text-xs text-brand-300">
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
        elements.push(<hr key={`hr-${key++}`} className="my-6 border-dark-850" />);
        continue;
      }

      if (line.startsWith('# ')) {
        elements.push(
          <h2 key={`h1-${key++}`} className="text-lg font-bold text-dark-50 tracking-tight font-mono mt-6 mb-3 border-b border-dark-850 pb-2">
            {parseInlineStyles(line.substring(2))}
          </h2>
        );
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h3 key={`h2-${key++}`} className="text-sm font-semibold text-dark-100 font-mono mt-5 mb-2">
            {parseInlineStyles(line.substring(3))}
          </h3>
        );
        continue;
      }
      if (line.startsWith('### ')) {
        elements.push(
          <h4 key={`h3-${key++}`} className="text-xs font-semibold text-dark-300 font-mono mt-4 mb-2">
            {parseInlineStyles(line.substring(4))}
          </h4>
        );
        continue;
      }

      if (line.startsWith('- ') || line.startsWith('* ')) {
        elements.push(
          <ul key={`ul-${key++}`} className="list-disc pl-5 my-1.5 font-mono text-xs text-dark-300">
            <li>{parseInlineStyles(line.substring(2))}</li>
          </ul>
        );
        continue;
      }
      if (/^\d+\.\s/.test(line)) {
        const content = line.replace(/^\d+\.\s/, '');
        elements.push(
          <ol key={`ol-${key++}`} className="list-decimal pl-5 my-1.5 font-mono text-xs text-dark-300">
            <li>{parseInlineStyles(content)}</li>
          </ol>
        );
        continue;
      }

      if (line.trim() === '') {
        continue;
      }

      elements.push(
        <p key={`p-${key++}`} className="my-2 text-xs text-dark-300 font-mono leading-relaxed">
          {parseInlineStyles(line)}
        </p>
      );
    }

    return elements;
  };

  const toggleSection = (section: string) => {
    setExpandedSection(expandedSection === section ? null : section);
  };

  // Helper to build list details inside sections
  const renderItemSection = (title: string, id: string, items?: string[], content?: string) => {
    const isExpanded = expandedSection === id;
    if (!items && !content) return null;

    return (
      <div className="border border-dark-850 rounded-lg overflow-hidden bg-dark-950/20">
        <button
          onClick={() => toggleSection(id)}
          className="w-full flex items-center justify-between p-4 bg-dark-900/40 hover:bg-dark-900 font-mono text-xs font-semibold text-dark-200 cursor-pointer text-left transition-colors"
        >
          <span className="uppercase">{title}</span>
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
        <AnimatePresence initial={false}>
          {isExpanded && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 'auto' }}
              exit={{ height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <div className="p-4 border-t border-dark-850 bg-dark-950/40 space-y-2">
                {content && <p className="text-xs text-dark-300 font-mono leading-relaxed">{content}</p>}
                {items && items.length > 0 && (
                  <ul className="list-disc pl-5 font-mono text-xs text-dark-300 space-y-2">
                    {items.map((item, idx) => (
                      <li key={idx}>{parseInlineStyles(item)}</li>
                    ))}
                  </ul>
                )}
                {items && items.length === 0 && !content && (
                  <p className="text-xs font-mono text-dark-400 italic">No significant issues detected.</p>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    );
  };

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6 print:border-none print:bg-white print:text-black">
      {/* Action panel bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-dark-850 pb-4 mb-5 gap-4 print:hidden">
        <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
          <span>06.</span> PIPELINE OUTPUT AUDIT REPORT
        </h2>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          {/* View Toggles */}
          <div className="flex border border-dark-850 rounded bg-dark-950 p-1 mr-2 text-xs font-mono">
            <button
              onClick={() => setActiveTab('structured')}
              className={`px-3 py-1 rounded cursor-pointer transition-colors ${activeTab === 'structured' ? 'bg-cyan-500 text-dark-950 font-bold' : 'text-dark-400 hover:text-dark-200'}`}
            >
              INTERACTIVE
            </button>
            <button
              onClick={() => setActiveTab('markdown')}
              className={`px-3 py-1 rounded cursor-pointer transition-colors ${activeTab === 'markdown' ? 'bg-cyan-500 text-dark-950 font-bold' : 'text-dark-400 hover:text-dark-200'}`}
            >
              RAW MARKDOWN
            </button>
          </div>

          {/* Copy Report */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-2.5 py-1.5 rounded bg-dark-950 cursor-pointer transition-all"
            title="Copy report to clipboard"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Clipboard className="w-3.5 h-3.5" />}
            <span className="hidden md:inline">COPY</span>
          </button>

          {/* Export MD */}
          <button
            onClick={handleExportMarkdown}
            className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-2.5 py-1.5 rounded bg-dark-950 cursor-pointer transition-all"
            title="Export to Markdown file"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden md:inline">EXPORT MD</span>
          </button>

          {/* Export PDF */}
          <button
            onClick={handleExportPDF}
            className="flex items-center gap-1.5 text-xs font-mono text-dark-400 hover:text-cyan-400 border border-dark-800 hover:border-cyan-500/20 px-2.5 py-1.5 rounded bg-dark-950 cursor-pointer transition-all"
            title="Print to PDF"
          >
            <FileText className="w-3.5 h-3.5" />
            <span className="hidden md:inline">PRINT PDF</span>
          </button>
        </div>
      </div>

      {/* Print Header only shown during print exports */}
      <div className="hidden print:block mb-8 font-mono">
        <h1 className="text-2xl font-bold border-b-2 border-black pb-2 uppercase">DevMind Code Audit Summary Report</h1>
        <p className="text-xs text-gray-600 mt-2">
          Generated on {new Date().toLocaleString()} for {parsedReport?.repository?.owner}/{parsedReport?.repository?.name}
        </p>
      </div>

      {/* Rendered content */}
      <div className="print:block">
        {activeTab === 'markdown' || isFallback ? (
          <div className="overflow-y-auto max-h-[600px] pr-2 print:max-h-none print:pr-0">
            {isFallback && (
              <div className="border border-amber-500/20 bg-amber-950/10 rounded-lg p-4 mb-5 text-amber-300 font-mono text-xs flex items-start gap-3">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <div>
                  <p className="font-semibold uppercase">Fallback Mode Active</p>
                  <p className="mt-1 text-dark-400">
                    The backend AI reasoning model is currently offline or failed limits checks. Showing local static heuristic analysis metrics.
                  </p>
                </div>
              </div>
            )}
            {renderMarkdownText(analysisResult)}
          </div>
        ) : (
          <div className="space-y-3 font-mono text-xs">
            {/* 1. Executive Summary */}
            {renderItemSection('Executive Summary', 'summary', undefined, aiOutput?.executive_summary)}

            {/* 2. Architecture & Modules */}
            {(parsedReport?.task_type === 'explain' || aiOutput?.high_level_architecture || aiOutput?.entry_points || aiOutput?.important_modules || aiOutput?.data_flow) && (
              <div className="border border-dark-850 rounded-lg overflow-hidden bg-dark-950/20">
                <button
                  onClick={() => toggleSection('architecture')}
                  className="w-full flex items-center justify-between p-4 bg-dark-900/40 hover:bg-dark-900 font-mono text-xs font-semibold text-dark-200 cursor-pointer text-left transition-colors"
                >
                  <span>STRUCTURE & CODE ARCHITECTURE</span>
                  {expandedSection === 'architecture' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                <AnimatePresence initial={false}>
                  {expandedSection === 'architecture' && (
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: 'auto' }}
                      exit={{ height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="p-4 border-t border-dark-850 bg-dark-950/40 space-y-4">
                        {aiOutput?.high_level_architecture && aiOutput.high_level_architecture.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">High-Level Layers:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.high_level_architecture.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.entry_points && aiOutput.entry_points.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Entry Points:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.entry_points.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.important_modules && aiOutput.important_modules.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Primary Modules:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.important_modules.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.data_flow ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Data Flow Description:</h4>
                            <p className="text-dark-300 leading-relaxed">{aiOutput.data_flow}</p>
                          </div>
                        ) : null}
                        {!(aiOutput?.high_level_architecture?.length || aiOutput?.entry_points?.length || aiOutput?.important_modules?.length || aiOutput?.data_flow) && (
                          <p className="text-xs font-mono text-dark-400 italic">No significant issues detected.</p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
 
            {/* 3. Strengths */}
            {renderItemSection('Key Strengths', 'strengths', aiOutput?.strengths)}
 
            {/* 4. Improvements */}
            {renderItemSection('Improvements & Weaknesses', 'improvements', aiOutput?.improvements || aiOutput?.risk_areas)}
 
            {/* 5. Recommendations */}
            {renderItemSection('Actionable Recommendations', 'recommendations', aiOutput?.recommendations)}
 
            {/* 6. Security Observations */}
            {renderItemSection('Security Observations', 'security', aiOutput?.security_observations)}
 
            {/* 7. Performance Observations */}
            {renderItemSection('Performance Observations', 'performance', aiOutput?.performance_observations || aiOutput?.performance_concerns)}
 
            {/* 8. Testing Recommendations */}
            {(parsedReport?.task_type === 'tests' || aiOutput?.unit_test_suggestions || aiOutput?.integration_test_suggestions || aiOutput?.coverage_status || aiOutput?.mock_opportunities) && (
              <div className="border border-dark-850 rounded-lg overflow-hidden bg-dark-950/20">
                <button
                  onClick={() => toggleSection('testing')}
                  className="w-full flex items-center justify-between p-4 bg-dark-900/40 hover:bg-dark-900 font-mono text-xs font-semibold text-dark-200 cursor-pointer text-left transition-colors"
                >
                  <span>TESTING RECOMMENDATIONS</span>
                  {expandedSection === 'testing' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                <AnimatePresence initial={false}>
                  {expandedSection === 'testing' && (
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: 'auto' }}
                      exit={{ height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="p-4 border-t border-dark-850 bg-dark-950/40 space-y-4">
                        {aiOutput?.unit_test_suggestions && aiOutput.unit_test_suggestions.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Unit Tests:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.unit_test_suggestions.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.integration_test_suggestions && aiOutput.integration_test_suggestions.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Integration Tests:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.integration_test_suggestions.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.mock_opportunities && aiOutput.mock_opportunities.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Mock Targets:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.mock_opportunities.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.coverage_status && aiOutput.coverage_status.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Coverage Gap Areas:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.coverage_status.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {!(aiOutput?.unit_test_suggestions?.length || aiOutput?.integration_test_suggestions?.length || aiOutput?.mock_opportunities?.length || aiOutput?.coverage_status?.length) && (
                          <p className="text-xs font-mono text-dark-400 italic">No significant issues detected.</p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
 
            {/* 9. Bug Finder Observations */}
            {(parsedReport?.task_type === 'bugs' || aiOutput?.logical_issues || aiOutput?.error_prone_patterns || aiOutput?.null_handling_concerns || aiOutput?.async_concerns || aiOutput?.resource_management_observations) && (
              <div className="border border-dark-850 rounded-lg overflow-hidden bg-dark-950/20">
                <button
                  onClick={() => toggleSection('bugs')}
                  className="w-full flex items-center justify-between p-4 bg-dark-900/40 hover:bg-dark-900 font-mono text-xs font-semibold text-dark-200 cursor-pointer text-left transition-colors"
                >
                  <span>POTENTIAL BUGS & CODE DEFECTS</span>
                  {expandedSection === 'bugs' ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>
                <AnimatePresence initial={false}>
                  {expandedSection === 'bugs' && (
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: 'auto' }}
                      exit={{ height: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <div className="p-4 border-t border-dark-850 bg-dark-950/40 space-y-4">
                        {aiOutput?.logical_issues && aiOutput.logical_issues.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Logical Flaws:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.logical_issues.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.error_prone_patterns && aiOutput.error_prone_patterns.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Error Prone Code Patterns:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.error_prone_patterns.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.null_handling_concerns && aiOutput.null_handling_concerns.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Null Handling Flaws:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.null_handling_concerns.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.async_concerns && aiOutput.async_concerns.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Async / Connection Issues:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.async_concerns.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {aiOutput?.resource_management_observations && aiOutput.resource_management_observations.length > 0 ? (
                          <div>
                            <h4 className="text-dark-400 font-bold uppercase mb-2 text-[10px]">Resource Management / Leaks:</h4>
                            <ul className="list-disc pl-5 space-y-1.5 text-dark-300">
                              {aiOutput.resource_management_observations.map((item, i) => <li key={i}>{parseInlineStyles(item)}</li>)}
                            </ul>
                          </div>
                        ) : null}
                        {!(aiOutput?.logical_issues?.length || aiOutput?.error_prone_patterns?.length || aiOutput?.null_handling_concerns?.length || aiOutput?.async_concerns?.length || aiOutput?.resource_management_observations?.length) && (
                          <p className="text-xs font-mono text-dark-400 italic">No significant issues detected.</p>
                        )}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
