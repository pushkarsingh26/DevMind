import React from 'react';
import { motion } from 'framer-motion';
import { useAnalysisData } from '../context/AnalysisContext';
import { RepositoryAnalysisPanel } from '../components/RepositoryAnalysisPanel';
import { EmptyState, Button } from '../components/ui';
import { BarChart3, Database, Play } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const RepositoryAnalysisPage: React.FC = () => {
  const { parsedReport } = useAnalysisData();
  const navigate = useNavigate();

  const repositoryId = parsedReport?.repository?.id ?? null;
  const repositoryName = parsedReport?.repository?.name ?? '';

  return (
    <div className="space-y-6 text-left">
      {/* Page Title Section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-xl font-extrabold text-dark-50 font-display tracking-tight flex items-center gap-2.5">
            <BarChart3 className="w-6 h-6 text-cyan-accent" />
            <span>Repository Architecture Analysis</span>
          </h1>
          <p className="text-xs text-dark-400 font-mono mt-1">
            {repositoryId ? `Active Codebase: ${repositoryName} (ID: ${repositoryId})` : 'Analyze structural issues, circular imports, dead code, and hotspots.'}
          </p>
        </div>
      </div>

      {/* Main Panel Content */}
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: 'easeOut' }}
      >
        {repositoryId ? (
          <RepositoryAnalysisPanel repositoryId={repositoryId} />
        ) : (
          <EmptyState
            title="No Active Repository Selected"
            description="You must select or upload a target repository first to compile the structural intelligence metrics."
            icon={<Database className="w-8 h-8 text-cyan-accent animate-pulse" />}
            action={
              <Button variant="primary" glow onClick={() => navigate('/repositories')} className="flex items-center gap-2">
                <Play className="w-3.5 h-3.5 fill-dark-950 text-dark-950" />
                <span>SELECT REPOSITORY</span>
              </Button>
            }
          />
        )}
      </motion.div>
    </div>
  );
};

export default RepositoryAnalysisPage;
