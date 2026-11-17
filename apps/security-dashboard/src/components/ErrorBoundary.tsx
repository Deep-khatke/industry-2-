import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-xl mx-auto my-12 bg-white border border-[#ebebeb] rounded-3xl shadow-[0_4px_24px_rgba(0,0,0,0.06)] text-center font-sans">
          <div className="w-12 h-12 mx-auto rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-4">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <h3 className="text-base font-extrabold text-[#111111]">
            {this.props.fallbackTitle || 'Section Display Interrupted'}
          </h3>
          <p className="text-xs text-[#767676] font-medium mt-1 mb-4">
            A temporary render error occurred while formatting this view. The rest of the dashboard remains operational.
          </p>
          {this.state.error && (
            <div className="text-left font-mono text-[11px] p-3 bg-[#fafafa] border border-zinc-200 rounded-2xl text-[#c00] overflow-x-auto mb-4 max-h-32">
              {this.state.error.message || String(this.state.error)}
            </div>
          )}
          <button
            onClick={this.handleReset}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-[#e60023] hover:bg-[#ad081b] text-white text-xs font-bold transition-transform active:scale-95 shadow-sm"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reload View</span>
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

