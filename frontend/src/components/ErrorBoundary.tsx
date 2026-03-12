/**
 * Error Boundary — перехватывает рендер-ошибки и показывает заглушку
 * вместо белой страницы.
 */

import React, { Component, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[ErrorBoundary] Перехвачена ошибка рендера:', error, info)
  }

  handleReload = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
          <div className="text-center max-w-sm">
            <div className="text-5xl mb-4">⚠️</div>
            <h1 className="text-xl font-bold text-slate-800 mb-2">
              Произошла ошибка
            </h1>
            <p className="text-slate-500 mb-6 text-sm">
              Что-то пошло не так. Пожалуйста, вернитесь на главную или обновите страницу.
            </p>
            {this.state.error && (
              <p className="text-xs text-red-400 mb-4 font-mono break-all">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={this.handleReload}
              className="btn-primary w-full"
            >
              На главную
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
