import { useState, useRef, useEffect } from 'react'
import { askQuestion } from '../services/api'
import MessageBubble from '../components/MessageBubble'
import Loader from '../components/Loader'

export default function Copilot() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Copilot online. Ask about any equipment, incident, or procedure across the indexed documents.',
      sources: []
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = { role: 'user', content: input, sources: [] }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const result = await askQuestion(input)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: result.answer,
        sources: result.sources || []
      }])
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'COPILOT ERROR — could not reach the backend. Confirm the API is running on port 8000 and try again.',
        sources: [],
        isError: true
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const suggestions = [
    'Why did Pump P-104 fail in March 2024?',
    'What is the lubrication interval for P-104?',
    'What is the emergency shutdown procedure for P-104?'
  ]

  return (
    <div className="copilot">
      <div className="copilot__header">
        <div>
          <span className="eyebrow">EXPERT KNOWLEDGE COPILOT</span>
          <h2 className="copilot__title">Ask the plant anything</h2>
        </div>
      </div>

      <div className="copilot__panel">
        <div className="copilot__messages" ref={scrollRef}>
          {messages.map((msg, i) => (
            <MessageBubble key={i} message={msg} />
          ))}
          {loading && <Loader />}
        </div>

        {messages.length === 1 && (
          <div className="suggestions">
            {suggestions.map((s, i) => (
              <button key={i} className="suggestion-chip" onClick={() => setInput(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        <div className="copilot__input-row">
          <textarea
            className="copilot__input"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask about an asset, incident, or procedure…"
            rows={1}
          />
          <button
            className="btn btn--primary"
            onClick={sendMessage}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
