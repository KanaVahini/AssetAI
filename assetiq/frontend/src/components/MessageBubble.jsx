import SourceCard from './SourceCard'

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={'msg-row' + (isUser ? ' msg-row--user' : '')}>
      <div className={
        'msg-bubble' +
        (isUser ? ' msg-bubble--user' : '') +
        (message.isError ? ' msg-bubble--error' : '')
      }>
        {message.content}
      </div>

      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="msg-sources">
          {message.sources.map((source, i) => (
            <SourceCard key={i} filename={source} />
          ))}
        </div>
      )}
    </div>
  )
}
