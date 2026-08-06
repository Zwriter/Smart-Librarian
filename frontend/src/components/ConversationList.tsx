import { useEffect, useRef } from 'react'
import type { ConversationMessage } from '../types/api'
import { LoadingIndicator } from './LoadingIndicator'
import { MessageBubble } from './MessageBubble'

type ConversationListProps = {
  messages: ConversationMessage[]
  isLoading?: boolean
}

export function ConversationList({ messages, isLoading = false }: ConversationListProps) {
  const conversationRef = useRef<HTMLDivElement>(null)
  const shouldFollowLatest = useRef(true)

  useEffect(() => {
    const conversation = conversationRef.current
    if (!conversation || !shouldFollowLatest.current) {
      return
    }

    if ('scrollTo' in conversation && typeof conversation.scrollTo === 'function') {
      conversation.scrollTo({ top: conversation.scrollHeight, behavior: 'smooth' })
    } else {
      conversation.scrollTop = conversation.scrollHeight
    }
  }, [messages.length, isLoading])

  function handleScroll() {
    const conversation = conversationRef.current
    if (!conversation) {
      return
    }

    const distanceFromLatest = conversation.scrollHeight - conversation.scrollTop - conversation.clientHeight
    shouldFollowLatest.current = distanceFromLatest < 80
  }

  return (
    <div
      className="conversation"
      ref={conversationRef}
      onScroll={handleScroll}
      role="region"
      aria-label="Conversation history"
      aria-live="polite"
    >
      {!messages.length && !isLoading && (
        <div className="empty-state">
          <span className="book-mark" aria-hidden="true">✦</span>
          <p>Describe a mood, a genre, or the last story you could not put down.</p>
          <span className="prompt-hint">Try “A mysterious story with an unforgettable setting.”</span>
        </div>
      )}
      {messages.map((message, index) => (
        <MessageBubble key={`${message.role}-${index}`} message={message} />
      ))}
      <div className="loading-slot">{isLoading && <LoadingIndicator />}</div>
    </div>
  )
}