import { useState, useRef, useEffect } from 'react'
import { FiMessageCircle, FiX, FiSend, FiUser, FiMic, FiMicOff } from 'react-icons/fi'
import { envoyerMessage, versHistorique } from '../../services/chatbot.js'
import ReponseAssistant from './ReponseAssistant.jsx'

const SUGGESTIONS = [
  "Comment déposer une plainte ?",
  "Quels documents apporter au tribunal ?",
  "Mon voisin occupe une partie de mon terrain : que faire ?",
  "Comment suivre mon dossier ?",
  "Comment prendre un rendez-vous ?",
]

export default function AssistantJuridique() {
  const [ouvert, setOuvert]     = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant', accueil: true,
      content: "Bonjour. Je suis l'Assistant juridique de SunuTribunal. Posez-moi votre question sur une démarche "
             + "au tribunal, vos droits ou les pièces à fournir — par écrit ou au micro."
    }
  ])
  const [input, setInput]         = useState('')
  const [loading, setLoading]     = useState(false)
  const [ecoute, setEcoute]       = useState(false)
  const [microSupporte, setMicroSupporte] = useState(true)
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
      setMicroSupporte(false)
    }
  }, [])

  const demarrerMicro = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      alert('Reconnaissance vocale non supportee. Utilisez Chrome.')
      return
    }
    const recognition = new SpeechRecognition()
    recognition.lang = 'fr-FR'
    recognition.continuous = false
    recognition.interimResults = true

    recognition.onstart = () => setEcoute(true)

    recognition.onresult = (event) => {
      const transcript = Array.from(event.results)
        .map(r => r[0].transcript)
        .join('')
      setInput(transcript)
    }

    recognition.onend = () => {
      setEcoute(false)
    }

    recognition.onerror = () => setEcoute(false)

    recognitionRef.current = recognition
    recognition.start()
  }

  const arreterMicro = () => {
    recognitionRef.current?.stop()
    setEcoute(false)
  }

  const envoyer = async (texte) => {
    const question = texte || input.trim()
    if (!question || loading) return

    // Mémoire de la conversation : les 10 derniers échanges (sans l'accueil ni les erreurs)
    const historique = versHistorique(messages)
    setMessages(m => [...m, { role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      const reponse = await envoyerMessage(question, historique)
      setMessages(m => [...m, { role: 'assistant', content: reponse }])
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', erreur: true, content: err.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Bouton flottant */}
      <button
        onClick={() => setOuvert(!ouvert)}
        // Mobile / APK : au-dessus de la barre de navigation du bas, sans la recouvrir
        className="fixed bottom-[4.75rem] right-4 lg:bottom-6 lg:right-6 z-50 w-14 h-14 rounded-full bg-justice-500 text-white shadow-2xl flex items-center justify-center hover:bg-justice-400 transition-all active:scale-95"
        style={{ animation: ouvert ? 'none' : 'pulse-sos 3s infinite' }}>
        {ouvert
          ? <FiX className="w-6 h-6" />
          : <FiMessageCircle className="w-6 h-6" />
        }
      </button>

      {/* Fenetre chat */}
      {ouvert && (
        <div className="fixed inset-x-3 bottom-[8.5rem] lg:inset-x-auto lg:right-6 lg:bottom-24 lg:w-80 z-50 bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden animate-slide-in"
          style={{ height: 'min(480px, calc(100vh - 12rem))' }}>

          {/* Header */}
          <div className="bg-justice-500 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
                <FiMessageCircle className="w-4 h-4 text-white" />
              </div>
              <div>
                <p className="text-white font-semibold text-sm">Assistant juridique</p>
                <p className="text-white/70 text-xs">Assistant juridique SunuTribunal</p>
              </div>
            </div>
            <button onClick={() => setOuvert(false)} aria-label="Fermer l'assistant">
              <FiX className="w-5 h-5 text-white/70 hover:text-white" />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3 bg-gray-50">
            {messages.map((m, i) => (
              <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                  m.role === 'user' ? 'bg-navy-700' : 'bg-justice-500'
                }`}>
                  {m.role === 'user'
                    ? <FiUser className="w-3.5 h-3.5 text-white" />
                    : <span className="text-white text-xs font-bold">ST</span>
                  }
                </div>
                <div className={`px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'max-w-56 bg-navy-700 text-white rounded-tr-sm whitespace-pre-wrap'
                    : 'flex-1 min-w-0 bg-white text-gray-700 shadow-sm border border-gray-100 rounded-tl-sm'
                }`}>
                  {m.role === 'user'
                    ? m.content
                    : <ReponseAssistant texte={m.content} copiable={!m.accueil && !m.erreur} />}
                </div>
              </div>
            ))}

            {/* Indicateur ecoute */}
            {ecoute && (
              <div className="flex justify-center">
                <div className="bg-red-50 border border-red-200 rounded-full px-4 py-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-blink" />
                  <span className="text-xs text-red-600 font-semibold">En ecoute... parlez maintenant</span>
                </div>
              </div>
            )}

            {/* Chargement */}
            {loading && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-justice-500 flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs font-bold">ST</span>
                </div>
                <div className="bg-white border border-gray-100 shadow-sm rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1 items-center">
                  <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Suggestions */}
          {messages.length === 1 && (
            <div className="px-3 py-2 bg-gray-50 border-t border-gray-100">
              <p className="text-xs text-gray-500 mb-2">Questions fréquentes :</p>
              <div className="flex flex-wrap gap-1">
                {SUGGESTIONS.slice(0, 3).map(s => (
                  <button key={s} onClick={() => envoyer(s)}
                    className="text-xs bg-white border border-gray-200 text-gray-600 px-2 py-1 rounded-full hover:border-justice-400 hover:text-justice-600 transition-colors">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Input */}
          <div className="px-3 py-3 bg-white border-t border-gray-100">
            {ecoute && input && (
              <div className="bg-gray-50 rounded-xl px-3 py-2 mb-2 text-sm text-gray-600 italic border border-gray-200">
                {input}
              </div>
            )}
            <div className="flex gap-2 items-center">
              {microSupporte && (
                <button
                  onClick={ecoute ? arreterMicro : demarrerMicro}
                  className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all flex-shrink-0 ${
                    ecoute
                      ? 'bg-red-500 text-white animate-pulse'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}>
                  {ecoute
                    ? <FiMicOff className="w-4 h-4" />
                    : <FiMic className="w-4 h-4" />
                  }
                </button>
              )}
              <input
                className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-justice-400 bg-gray-50"
                placeholder={ecoute ? "En écoute..." : "Posez votre question..."}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && envoyer()}
                disabled={loading || ecoute}
              />
              <button
                onClick={() => envoyer()}
                disabled={!input.trim() || loading}
                className="w-9 h-9 rounded-xl bg-justice-500 text-white flex items-center justify-center hover:bg-justice-400 transition-colors disabled:opacity-50 flex-shrink-0">
                <FiSend className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[11px] text-gray-500 text-center mt-2 leading-snug">
              Information juridique générale — ne remplace pas l'avis d'un avocat ou d'un greffier.
            </p>
          </div>
        </div>
      )}
    </>
  )
}