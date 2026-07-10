import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw, LayoutDashboard } from 'lucide-react';
import { Card, CardHeader, CardContent, CardFooter, Button } from './ui';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, errorInfo: null };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught boundary error:', error, errorInfo);
    this.setState({
      error,
      errorInfo
    });
  }

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoDashboard = () => {
    window.location.href = '/dashboard';
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6 text-left">
          <Card variant="soft" className="w-full max-w-2xl border-2 border-red-accent/30 bg-red-accent/5">
            <CardHeader className="flex items-center gap-3">
              <div className="p-2.5 bg-red-500/10 border border-red-500/25 rounded-xl text-red-400">
                <AlertCircle className="w-6 h-6 animate-bounce" />
              </div>
              <div>
                <h2 className="text-base font-bold text-dark-50 font-display">Something Went Wrong</h2>
                <p className="text-xs text-dark-400 font-mono mt-0.5">An unexpected exception was intercepted by ErrorBoundary</p>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-dark-300 leading-relaxed font-sans">
                DevMind encountered a render-phase crash. Please inspect the trace details below or try resetting the workspace dashboard.
              </p>
              {this.state.error && (
                <div className="bg-[#050811] border border-border-primary rounded-xl p-4 space-y-2">
                  <span className="text-[10px] text-red-400 font-mono font-bold uppercase block">Error Details:</span>
                  <span className="text-xs text-dark-100 font-mono block font-semibold">{this.state.error.toString()}</span>
                  {this.state.errorInfo && (
                    <pre className="overflow-x-auto text-[9px] text-dark-500 font-mono max-h-[160px] leading-normal pt-2 border-t border-border-primary/50 scrollbar-thin select-text">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              )}
            </CardContent>
            <CardFooter className="flex gap-4 border-t border-border-primary/40 pt-4">
              <Button
                variant="primary"
                glow
                onClick={this.handleReload}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <RefreshCw className="w-4 h-4" />
                <span>RELOAD WORKSPACE</span>
              </Button>
              <Button
                variant="glass"
                onClick={this.handleGoDashboard}
                className="flex-1 flex items-center justify-center gap-2"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>GO TO DASHBOARD</span>
              </Button>
            </CardFooter>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
