import React, { useState } from 'react';
import { Terminal, Clipboard, Check } from 'lucide-react';
import { useAnalysis } from '../hooks/useAnalysis';

export const OutputPanel: React.FC = () => {
  const { analysisResult } = useAnalysis();
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    if (!analysisResult) return;
    navigator.clipboard.writeText(analysisResult);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!analysisResult) {
    return (
      <div className="bg-dark-900 border border-dark-800 rounded-lg p-8 text-center">
        <div className="flex justify-center mb-3">
          <Terminal className="w-8 h-8 text-dark-700" />
        </div>
        <p className="text-sm font-mono text-dark-500">
          No analysis yet. Fill in target repository and start the pipeline.
        </p>
      </div>
    );
  }

  // A helper function to parse mock Markdown blocks into React elements
  const renderMarkdown = (markdown: string) => {
    const lines = markdown.split('\n');
    const elements: React.ReactNode[] = [];
    let key = 0;
    
    let inCodeBlock = false;
    let codeBlockContent: string[] = [];
    let codeBlockLang = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      // Code Block Toggles
      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          // Close block
          const content = codeBlockContent.join('\n');
          elements.push(
            <div key={`code-${key++}`} className="my-4 bg-dark-950 border border-dark-800 rounded-md overflow-hidden font-mono">
              {codeBlockLang && (
                <div className="bg-dark-900 border-b border-dark-800 px-4 py-2 flex items-center justify-between text-[11px] text-dark-400">
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
          // Open block
          codeBlockLang = line.replace('```', '').trim();
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeBlockContent.push(line);
        continue;
      }

      // Horizontal Rule
      if (line.trim() === '---') {
        elements.push(<hr key={`hr-${key++}`} className="my-6 border-dark-800" />);
        continue;
      }

      // Headings
      if (line.startsWith('# ')) {
        elements.push(
          <h2 key={`h1-${key++}`} className="text-xl font-bold text-dark-50 tracking-tight font-mono mt-6 mb-3">
            {parseInlineStyles(line.substring(2))}
          </h2>
        );
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(
          <h3 key={`h2-${key++}`} className="text-base font-semibold text-dark-100 font-mono mt-5 mb-2">
            {parseInlineStyles(line.substring(3))}
          </h3>
        );
        continue;
      }
      if (line.startsWith('### ')) {
        elements.push(
          <h4 key={`h3-${key++}`} className="text-sm font-semibold text-dark-200 font-mono mt-4 mb-2">
            {parseInlineStyles(line.substring(4))}
          </h4>
        );
        continue;
      }

      // Lists
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

      // Empty Lines
      if (line.trim() === '') {
        continue;
      }

      // Regular Paragraph
      elements.push(
        <p key={`p-${key++}`} className="my-2 text-xs text-dark-300 font-mono leading-relaxed">
          {parseInlineStyles(line)}
        </p>
      );
    }

    return elements;
  };

  // Helper to parse inline styles like bold (**text**) and code (`text`)
  const parseInlineStyles = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    
    // Simple parser matching double asterisks or backticks
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

  return (
    <div className="bg-dark-900 border border-dark-800 rounded-lg p-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-dark-800 pb-4 mb-4">
        <h2 className="text-base font-semibold text-dark-100 font-mono flex items-center gap-2">
          <span>04.</span> PIPELINE OUTPUT REPORT
        </h2>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-2 text-xs font-mono text-dark-400 hover:text-brand-400 border border-dark-800 hover:border-brand-500/30 px-3 py-1.5 rounded bg-dark-950 cursor-pointer"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5 text-emerald-400" />
              <span>COPIED!</span>
            </>
          ) : (
            <>
              <Clipboard className="w-3.5 h-3.5" />
              <span>COPY REPORT</span>
            </>
          )}
        </button>
      </div>

      {/* Rendered content */}
      <div className="overflow-y-auto max-h-[500px] pr-2">
        {renderMarkdown(analysisResult)}
      </div>
    </div>
  );
};
