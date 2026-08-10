import type { ConversationMessage } from '../types/api'

type MessageBubbleProps = {
  message: ConversationMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const speaker = message.role === 'user' ? 'You' : 'Librarian'

  return (
    <article className={`message ${message.role}`} aria-label={`${speaker} message`}>
      <span className="message-role">{speaker}</span>
      <p className="message-content">{message.content}</p>
    </article>
  )
}