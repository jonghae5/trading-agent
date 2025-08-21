import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
  variant?: 'default' | 'report' | 'summary'
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({
  content,
  variant = 'default'
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'report':
        return {
          h1Color: 'text-gray-900',
          h2Color: 'text-gray-800',
          h3Color: 'text-gray-800',
          borderColor: 'border-gray-200',
          blockquoteBorder: 'border-blue-200',
          blockquoteBg: 'bg-gray-50',
          blockquoteText: 'text-gray-600',
          codeInlineBg: 'bg-gray-200',
          codeInlineText: 'text-gray-800',
          tableBorder: 'border-gray-300',
          tableHeaderBg: 'bg-gray-100',
          tableHeaderText: 'text-gray-700'
        }
      case 'summary':
        return {
          h1Color: 'text-blue-900',
          h2Color: 'text-blue-800',
          h3Color: 'text-blue-800',
          borderColor: 'border-blue-200',
          blockquoteBorder: 'border-blue-400',
          blockquoteBg: 'bg-blue-50',
          blockquoteText: 'text-blue-700',
          codeInlineBg: 'bg-blue-100',
          codeInlineText: 'text-blue-800',
          tableBorder: 'border-blue-300',
          tableHeaderBg: 'bg-blue-100',
          tableHeaderText: 'text-blue-700'
        }
      default:
        return {
          h1Color: 'text-gray-900',
          h2Color: 'text-gray-800',
          h3Color: 'text-gray-800',
          borderColor: 'border-gray-200',
          blockquoteBorder: 'border-gray-300',
          blockquoteBg: 'bg-gray-50',
          blockquoteText: 'text-gray-600',
          codeInlineBg: 'bg-gray-200',
          codeInlineText: 'text-gray-800',
          tableBorder: 'border-gray-300',
          tableHeaderBg: 'bg-gray-100',
          tableHeaderText: 'text-gray-700'
        }
    }
  }

  const styles = getVariantStyles()

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        h1: ({ children }) => (
          <h1 className={`text-xl font-bold ${styles.h1Color} mb-3 border-b ${styles.borderColor} pb-2`}>
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2 className={`text-lg font-semibold ${styles.h2Color} mb-2 mt-4`}>
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3 className={`text-base font-medium ${styles.h3Color} mb-2 mt-3`}>
            {children}
          </h3>
        ),
        h4: ({ children }) => (
          <h4 className={`text-sm font-medium ${styles.h3Color} mb-2 mt-2`}>
            {children}
          </h4>
        ),
        h5: ({ children }) => (
          <h5 className={`text-sm font-medium ${styles.h3Color} mb-1 mt-2`}>
            {children}
          </h5>
        ),
        h6: ({ children }) => (
          <h6 className={`text-xs font-medium ${styles.h3Color} mb-1 mt-2`}>
            {children}
          </h6>
        ),
        p: ({ children }) => (
          <p className="mb-3 text-gray-700 leading-relaxed">
            {children}
          </p>
        ),
        ul: ({ children }) => (
          <ul className="list-disc ml-5 mb-3 space-y-1">
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol className="list-decimal ml-5 mb-3 space-y-1">
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li className="text-gray-700">{children}</li>
        ),
        blockquote: ({ children }) => (
          <blockquote className={`border-l-4 ${styles.blockquoteBorder} pl-4 my-3 ${styles.blockquoteText} italic ${variant === 'summary' ? `${styles.blockquoteBg} py-2 rounded-r` : ''}`}>
            {children}
          </blockquote>
        ),
        code: ({ children, className }) => {
          const isInline = !className
          return isInline ? (
            <code className={`${styles.codeInlineBg} px-1.5 py-0.5 rounded text-sm font-mono ${styles.codeInlineText}`}>
              {children}
            </code>
          ) : (
            <code className="block bg-gray-800 text-gray-100 p-3 rounded text-sm font-mono overflow-x-auto">
              {children}
            </code>
          )
        },
        pre: ({ children }) => (
          <pre className="bg-gray-800 text-gray-100 p-3 rounded text-sm font-mono overflow-x-auto mb-3">
            {children}
          </pre>
        ),
        table: ({ children }) => (
          <div className="overflow-x-auto mb-3">
            <table className={`min-w-full divide-y divide-gray-200 border ${styles.tableBorder}`}>
              {children}
            </table>
          </div>
        ),
        thead: ({ children }) => (
          <thead className={styles.tableHeaderBg}>{children}</thead>
        ),
        tbody: ({ children }) => (
          <tbody className={`bg-white divide-y ${variant === 'summary' ? 'divide-blue-200' : 'divide-gray-200'}`}>
            {children}
          </tbody>
        ),
        tr: ({ children }) => <tr>{children}</tr>,
        th: ({ children }) => (
          <th className={`px-3 py-2 text-left text-xs font-medium ${styles.tableHeaderText} uppercase tracking-wider border-r ${styles.tableBorder}`}>
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td className={`px-3 py-2 text-sm text-gray-700 border-r ${styles.tableBorder}`}>
            {children}
          </td>
        ),
        strong: ({ children }) => (
          <strong className={`font-semibold ${variant === 'summary' ? 'text-blue-900' : 'text-gray-900'}`}>
            {children}
          </strong>
        ),
        em: ({ children }) => (
          <em className={`italic ${variant === 'summary' ? 'text-blue-700' : 'text-gray-700'}`}>
            {children}
          </em>
        ),
        a: ({ children, href }) => (
          <a
            href={href}
            className="text-blue-600 hover:text-blue-800 underline"
            target="_blank"
            rel="noopener noreferrer"
          >
            {children}
          </a>
        ),
        hr: () => (
          <hr className={`my-4 border-t ${styles.borderColor}`} />
        )
      }}
    >
      {content}
    </ReactMarkdown>
  )
}