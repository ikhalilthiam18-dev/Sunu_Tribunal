import { useState, useRef, useEffect } from 'react'
import { FiCpu, FiX, FiSend, FiMic, FiMicOff } from 'react-icons/fi'
import { envoyerMessageGreffe, versHistorique } from '../../services/chatbot.js'
import ReponseAssistant from '../common/ReponseAssistant.jsx'

const SUGGESTIONS_ADMIN = [
  "Rédige une convocation à une audience",
  "Rédige une notification de rejet de plainte",
  "Rédige une demande de pièces complémentaires",
  "Rédige une notification de décision rendue",
  "Rappelle les étapes d'enregistrement d'un courrier arrivé",
]

export default function AssistantAdmin() {
  const [ouvert, setOuvert]     = useState(false)
  const [messages, setMessages] = useState([
    {
      role: 'assistant', accueil: true,
      content: "Bonjour. Je suis l'Assistant du greffe. Je rédige vos courriers officiels, convocations et "
             + "notifications de décision, et je rappelle les étapes des procédures."
    }
  ])
  const [input, setInput]           = useState('')
  const [loading, setLoading]       = useState(false)
  const [ecoute, setEcoute]         = useState(false)
  const [microSupporte, setMicroSupporte] = useState(true)
  const messagesEndRef  = useRef(null)
  const recognitionRef  = useRef(null)

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
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.lang = 'fr-FR'
    recognition.continuous = false
    recognition.interimResults = true
    recognition.onstart  = () => setEcoute(true)
    recognition.onresult = (event) => {
      const transcript = Array.from(event.results).map(r => r[0].transcript).join('')
      setInput(transcript)
    }
    recognition.onend   = () => setEcoute(false)
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
      const reponse = await envoyerMessageGreffe(question, historique)
      setMessages(m => [...m, { role: 'assistant', content: reponse }])
    } catch (err) {
      setMessages(m => [...m, { role: 'assistant', erreur: true, content: err.message }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      {/* Bouton flottant admin */}
      <button
        onClick={() => setOuvert(!ouvert)}
        className="fixed bottom-5 right-4 lg:bottom-6 lg:right-6 z-50 w-14 h-14 rounded-full bg-navy-700 text-white shadow-2xl flex items-center justify-center hover:bg-navy-600 transition-all active:scale-95"
        title="Assistant du greffe" aria-label="Assistant du greffe">
        {ouvert
          ? <FiX className="w-6 h-6" />
          : <FiCpu className="w-6 h-6" />
        }
      </button>

      {/* Fenetre chat */}
      {ouvert && (
        <div className="fixed bottom-24 right-4 sm:right-6 z-50 w-[min(24rem,calc(100vw-2rem))] bg-white rounded-2xl shadow-2xl border border-gray-200 flex flex-col overflow-hidden animate-slide-in"
          style={{ height: 'min(520px, calc(100vh - 8rem))' }}>

          {/* Header */}
          <div className="bg-navy-700 px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gold-400/20 rounded-full flex items-center justify-center">
                <FiCpu className="w-4 h-4 text-gold-400" />
              </div>
              <div>
                <p className="text-white font-semibold text-sm">Assistant du greffe</p>
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
                <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold text-white ${
                  m.role === 'user' ? 'bg-justice-500' : 'bg-navy-700'
                }`}>
                  {m.role === 'user' ? 'G' : 'ST'}
                </div>
                <div className={m.role === 'user' ? 'max-w-64' : 'flex-1 min-w-0'}>
                  <div className={`px-3 py-2 rounded-2xl text-sm leading-relaxed ${
                    m.role === 'user'
                      ? 'bg-justice-500 text-white rounded-tr-sm whitespace-pre-wrap'
                      : 'bg-white text-gray-700 shadow-sm border border-gray-100 rounded-tl-sm'
                  }`}>
                    {m.role === 'user'
                      ? m.content
                      : <ReponseAssistant texte={m.content} copiable={!m.accueil && !m.erreur} />}
                  </div>
                </div>
              </div>
            ))}

            {/* Ecoute micro */}
            {ecoute && (
              <div className="flex justify-center">
                <div className="bg-red-50 border border-red-200 rounded-full px-4 py-2 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-red-500 animate-blink" />
                  <span className="text-xs text-red-600 font-semibold">En écoute...</span>
                </div>
              </div>
            )}

            {/* Chargement */}
            {loading && (
              <div className="flex gap-2">
                <div className="w-7 h-7 rounded-full bg-navy-700 flex items-center justify-center flex-shrink-0">
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
              <p className="text-xs text-gray-500 mb-2">Actions rapides :</p>
              <div className="flex flex-col gap-1">
                {SUGGESTIONS_ADMIN.slice(0, 3).map(s => (
                  <button key={s} onClick={() => envoyer(s)}
                    className="text-xs bg-white border border-gray-200 text-gray-600 px-3 py-1.5 rounded-lg hover:border-navy-400 hover:text-navy-700 transition-colors text-left">
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
                  {ecoute ? <FiMicOff className="w-4 h-4" /> : <FiMic className="w-4 h-4" />}
                </button>
              )}
              <input
                className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:border-navy-400 bg-gray-50"
                placeholder={ecoute ? "En écoute..." : "Décrivez le courrier ou la question..."}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && envoyer()}
                disabled={loading || ecoute}
              />
              <button
                onClick={() => envoyer()}
                disabled={!input.trim() || loading}
                className="w-9 h-9 rounded-xl bg-navy-700 text-white flex items-center justify-center hover:bg-navy-600 transition-colors disabled:opacity-50 flex-shrink-0">
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