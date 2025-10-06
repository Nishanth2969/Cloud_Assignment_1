


import { useState, useEffect, useRef } from 'react'
import { IoSend, IoRestaurant, IoLocationSharp, IoChatbubbleEllipses } from 'react-icons/io5'
import { MdRestaurantMenu } from 'react-icons/md'

function App() {
  const [messages, setMessages] = useState([
    { id: 1, text: "Hello! I'm your dining concierge. I can help you find great restaurants in Manhattan. What type of cuisine are you looking for?", sender: 'bot' }
  ])
  const [inputText, setInputText] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [sessionId] = useState(() => Math.random().toString(36).substr(2, 9))
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async () => {
      if (!inputText.trim()) return

      const userMessage = {
        id: Date.now(),
        text: inputText,
        sender: 'user'
      }

      setMessages(prev => [...prev, userMessage])
      setInputText('')
      setIsTyping(true)

      try {
        const apiUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000'

        const response = await fetch(`${apiUrl}/chatbot`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            messages: [
              {
                type: "unstructured",
                unstructured: {
                  text: inputText
                }
              }
            ]
          })
        })

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        const data = await response.json()

        // Extract the bot's response from the correct structure
        const botText = data.messages?.[0]?.unstructured?.text || "I'm sorry, I didn't understand that."

        const botMessage = {
          id: Date.now() + 1,
          text: botText,
          sender: 'bot'
        }

        setTimeout(() => {
          setMessages(prev => [...prev, botMessage])
          setIsTyping(false)
        }, 1000)

      } catch (error) {
        console.error('Error sending message:', error)
        const errorMessage = {
          id: Date.now() + 1,
          text: "I'm having trouble connecting right now. Please try again in a moment.",
          sender: 'bot'
        }

        setTimeout(() => {
          setMessages(prev => [...prev, errorMessage])
          setIsTyping(false)
        }, 1000)
      }
    }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  // Styles as React objects
  const styles = {
    app: {
      height: '100vh',
      width: '100vw',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1410 100%)',
      overflow: 'hidden',
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
    },
    header: {
      background: 'linear-gradient(135deg, rgba(20, 20, 20, 0.95) 0%, rgba(30, 20, 15, 0.98) 100%)',
      borderBottom: '1px solid rgba(212, 175, 55, 0.3)',
      padding: '1.5rem 2rem',
      backdropFilter: 'blur(20px)',
      boxShadow: '0 4px 30px rgba(0, 0, 0, 0.5)',
    },
    headerContent: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      maxWidth: '100%',
      margin: '0 auto',
    },
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    headerIcon: {
      color: '#d4af37',
      filter: 'drop-shadow(0 2px 8px rgba(212, 175, 55, 0.3))',
    },
    headerTitle: {
      fontSize: '2rem',
      fontWeight: '700',
      color: '#d4af37',
      margin: 0,
      letterSpacing: '0.5px',
      textShadow: '2px 2px 8px rgba(0, 0, 0, 0.5)',
    },
    headerSubtitle: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: '#e8e8e8',
      fontSize: '0.95rem',
      margin: 0,
    },
    mainContent: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      padding: '2rem',
      gap: '1.5rem',
    },
    chatSection: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      background: 'rgba(0, 0, 0, 0.3)',
      borderRadius: '20px',
      border: '1px solid rgba(212, 175, 55, 0.2)',
      backdropFilter: 'blur(10px)',
      overflow: 'hidden',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
    },
    chatHeader: {
      padding: '1.5rem 2rem',
      borderBottom: '1px solid rgba(212, 175, 55, 0.2)',
      background: 'rgba(212, 175, 55, 0.05)',
    },
    chatHeaderTitle: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      color: '#d4af37',
      fontSize: '1.5rem',
      fontWeight: '600',
      margin: '0 0 0.5rem 0',
    },
    chatHeaderSubtitle: {
      color: '#b8b8b8',
      fontSize: '0.95rem',
      margin: 0,
    },
    messagesContainer: {
      flex: 1,
      overflowY: 'auto',
      padding: '2rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '1.5rem',
    },
    message: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '1rem',
      animation: 'slideIn 0.3s ease',
    },
    messageUser: {
      flexDirection: 'row-reverse',
      justifyContent: 'flex-start',
    },
    messageBot: {
      flexDirection: 'row',
      justifyContent: 'flex-start',
    },
    avatar: {
      width: '44px',
      height: '44px',
      borderRadius: '50%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
      fontSize: '0.85rem',
      fontWeight: '600',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
    },
    avatarBot: {
      background: 'linear-gradient(135deg, rgba(50, 50, 50, 0.9), rgba(35, 35, 35, 0.95))',
      color: '#d4af37',
      border: '2px solid rgba(212, 175, 55, 0.4)',
    },
    avatarUser: {
      background: 'linear-gradient(135deg, #d4af37, #b8941f)',
      color: '#1a1a1a',
    },
    messageContent: {
      maxWidth: '60%',
      padding: '1rem 1.5rem',
      borderRadius: '16px',
      lineHeight: '1.6',
      fontSize: '1rem',
      wordWrap: 'break-word',
    },
    messageContentBot: {
      background: 'linear-gradient(135deg, rgba(45, 45, 45, 0.95), rgba(30, 30, 30, 0.98))',
      color: '#f5f5f5',
      border: '1px solid rgba(212, 175, 55, 0.3)',
      boxShadow: '0 4px 16px rgba(212, 175, 55, 0.15)',
    },
    messageContentUser: {
      background: 'linear-gradient(135deg, #d4af37, #c5a028)',
      color: '#1a1a1a',
      fontWeight: '500',
      boxShadow: '0 4px 16px rgba(212, 175, 55, 0.3)',
    },
    inputContainer: {
      padding: '1.5rem 2rem',
      borderTop: '1px solid rgba(212, 175, 55, 0.2)',
      background: 'rgba(0, 0, 0, 0.2)',
      display: 'flex',
      gap: '1rem',
      alignItems: 'flex-end',
    },
    textarea: {
      flex: 1,
      padding: '1rem 1.5rem',
      borderRadius: '16px',
      border: '2px solid rgba(212, 175, 55, 0.3)',
      background: 'rgba(20, 20, 20, 0.6)',
      color: '#ffffff',
      fontSize: '1rem',
      fontFamily: 'inherit',
      resize: 'none',
      outline: 'none',
      transition: 'all 0.3s ease',
      lineHeight: '1.5',
    },
    textareaFocus: {
      borderColor: '#d4af37',
      background: 'rgba(20, 20, 20, 0.8)',
      boxShadow: '0 0 0 3px rgba(212, 175, 55, 0.15)',
    },
    sendButton: {
      padding: '1rem 2rem',
      background: 'linear-gradient(135deg, #d4af37, #b8941f)',
      color: '#1a1a1a',
      border: 'none',
      borderRadius: '16px',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      boxShadow: '0 4px 16px rgba(212, 175, 55, 0.3)',
      minWidth: '120px',
      justifyContent: 'center',
    },
    sendButtonHover: {
      background: 'linear-gradient(135deg, #e6c547, #d4af37)',
      transform: 'translateY(-2px)',
      boxShadow: '0 6px 20px rgba(212, 175, 55, 0.4)',
    },
    sendButtonDisabled: {
      opacity: 0.5,
      cursor: 'not-allowed',
    },
    typingIndicator: {
      display: 'flex',
      gap: '6px',
      alignItems: 'center',
      padding: '0.5rem',
    },
    typingDot: {
      width: '10px',
      height: '10px',
      borderRadius: '50%',
      background: '#d4af37',
      animation: 'typing 1.4s infinite ease-in-out',
    },
  }

  const [isFocused, setIsFocused] = useState(false)
  const [isHovered, setIsHovered] = useState(false)

  return (
    <div style={styles.app}>
      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.5;
          }
          30% {
            transform: translateY(-8px);
            opacity: 1;
          }
        }

        *::-webkit-scrollbar {
          width: 8px;
        }

        *::-webkit-scrollbar-track {
          background: rgba(255, 255, 255, 0.05);
          border-radius: 4px;
        }

        *::-webkit-scrollbar-thumb {
          background: rgba(212, 175, 55, 0.4);
          border-radius: 4px;
        }

        *::-webkit-scrollbar-thumb:hover {
          background: rgba(212, 175, 55, 0.6);
        }

        textarea::placeholder {
          color: #888;
        }
      `}</style>

      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.headerLeft}>
            <div style={styles.headerIcon}>
              <MdRestaurantMenu size={40} />
            </div>
            <h1 style={styles.headerTitle}>Dining Concierge</h1>
          </div>
          <p style={styles.headerSubtitle}>
            <IoLocationSharp size={20} />
            Discover Manhattan's finest restaurants with AI
          </p>
        </div>
      </header>

      <div style={styles.mainContent}>
        <div style={styles.chatSection}>
          <div style={styles.chatHeader}>
            <h2 style={styles.chatHeaderTitle}>
              <IoChatbubbleEllipses size={28} />
              Chat with our Concierge
            </h2>
            <p style={styles.chatHeaderSubtitle}>
              Tell us your preferences and we'll find the perfect restaurant for you
            </p>
          </div>

          <div style={styles.messagesContainer}>
            {messages.map((message) => (
              <div
                key={message.id}
                style={{
                  ...styles.message,
                  ...(message.sender === 'user' ? styles.messageUser : styles.messageBot)
                }}
              >
                <div
                  style={{
                    ...styles.avatar,
                    ...(message.sender === 'bot' ? styles.avatarBot : styles.avatarUser)
                  }}
                >
                  {message.sender === 'bot' ? (
                    <IoRestaurant size={22} />
                  ) : (
                    'You'
                  )}
                </div>
                <div
                  style={{
                    ...styles.messageContent,
                    ...(message.sender === 'bot' ? styles.messageContentBot : styles.messageContentUser)
                  }}
                >
                  {message.text}
                </div>
              </div>
            ))}

            {isTyping && (
              <div style={{ ...styles.message, ...styles.messageBot }}>
                <div style={{ ...styles.avatar, ...styles.avatarBot }}>
                  <IoRestaurant size={22} />
                </div>
                <div style={{ ...styles.messageContent, ...styles.messageContentBot }}>
                  <div style={styles.typingIndicator}>
                    <span style={{ ...styles.typingDot, animationDelay: '0s' }}></span>
                    <span style={{ ...styles.typingDot, animationDelay: '0.2s' }}></span>
                    <span style={{ ...styles.typingDot, animationDelay: '0.4s' }}></span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div style={styles.inputContainer}>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyPress={handleKeyPress}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Ask me about restaurants in Manhattan..."
              rows="2"
              disabled={isTyping}
              style={{
                ...styles.textarea,
                ...(isFocused ? styles.textareaFocus : {})
              }}
            />
            <button
              onClick={sendMessage}
              disabled={!inputText.trim() || isTyping}
              onMouseEnter={() => setIsHovered(true)}
              onMouseLeave={() => setIsHovered(false)}
              style={{
                ...styles.sendButton,
                ...(isHovered && inputText.trim() && !isTyping ? styles.sendButtonHover : {}),
                ...(!inputText.trim() || isTyping ? styles.sendButtonDisabled : {})
              }}
            >
              <IoSend size={20} />
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

