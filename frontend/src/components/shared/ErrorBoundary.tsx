import { Component, type ErrorInfo, type ReactNode } from 'react';

export class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('DeforestWatch UI error', error, info);
  }

  render() {
    if (this.state.error) {
      return <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6"><section className="max-w-md rounded-md border border-red-200 bg-white p-6"><h1 className="text-lg font-semibold text-red-900">Dashboard unavailable</h1><p className="mt-2 text-sm text-slate-600">Refresh the page or return to the dashboard. The error was recorded locally.</p><button className="mt-4 rounded-md bg-slate-900 px-3 py-2 text-sm text-white" onClick={() => this.setState({ error: null })}>Try again</button></section></main>;
    }
    return this.props.children;
  }
}
