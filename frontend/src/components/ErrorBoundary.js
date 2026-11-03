import React from 'react';
import ErrorPage from './ErrorPage';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = {error: null};
  }

  static getDerivedStateFromError(error) {
    return {error};
  }

  componentDidCatch(error, info) {
    console.error('Error no controlado en la interfaz:', error, info?.componentStack);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) this.setState({error: null});
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <ErrorPage
        code={500}
        onRetry={() => this.setState({error: null})}
        onHome={this.props.onHome ? () => { this.setState({error: null}); this.props.onHome(); } : undefined}
      />
    );
  }
}
