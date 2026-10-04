import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth, homePathFor, PAGE_MOT_DE_PASSE } from '../context/AuthContext.jsx'
import { authAPI, messageErreur } from '../services/api.js'
import Logo from '../components/common/Logo.jsx'
import toast from 'react-hot-toast'
import heroDesktop from '../assets/hero-justice.jpg'
import hero1600 from '../assets/hero-justice-1600.jpg'
import heroMobile from '../assets/hero-justice-mobile.jpg'
import {
  FiCalendar, FiFileText, FiMapPin, FiAlertTriangle, FiMessageCircle, FiSearch,
  FiArrowRight, FiLogIn, FiLock, FiMail as FiMailIcon, FiEye, FiEyeOff,
  FiAlertCircle, FiX, FiMenu, FiUserPlus, FiSend, FiSmartphone
} from 'react-icons/fi'

// ── MODAL D'AUTHENTIFICATION ─────────────────────────
function AuthModal({ mode: initMode, onClose }) {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [mode, setMode]         = useState(initMode || 'login')   // login | register
  const [loading, setLoading]   = useState(false)
  const [showPass, setShowPass] = useState(false)
  const [error, setError]       = useState('')
  const [form, setForm] = useState({
    email: '', password: '', nom: '', prenom: '', telephone: ''
  })

  const set = (k, v) => { setForm(f => ({...f, [k]: v})); setError('') }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.email || !form.password) { setError('Veuillez remplir tous les champs.'); return }
    if (mode === 'register' && !form.nom) { setError('Le nom est requis.'); return }
    setLoading(true)
    try {
      if (mode === 'login') {
        const res = await authAPI.login({ email: form.email, password: form.password })
        const { access, user } = res.data
        const home = homePathFor(user.role)
        if (!home) { setError('Email ou mot de passe incorrect.'); return }
        login(user, access)
        toast.success('Bienvenue ' + user.nom + ' !')
        onClose()
        navigate(user.doit_changer_mdp ? PAGE_MOT_DE_PASSE : home, { replace: true })
      } else {
        await authAPI.register({
          email: form.email, password: form.password, password2: form.password,
          nom: form.nom, prenom: form.prenom, telephone: form.telephone,
          // Le rôle n'est pas envoyé : le serveur crée TOUJOURS un compte citoyen
        })
        toast.success('Compte cree ! Connectez-vous.')
        setMode('login')
        setForm(f => ({...f, password: ''}))
      }
    } catch (err) {
      if (mode === 'login' && err.response?.status === 401) {
        // Identifiants refusés (ou compte bloqué) : message unique du serveur, sans détail sur le compte
        setError(err.response.data?.detail || 'Email ou mot de passe incorrect.')
      } else {
        // Inscription (email déjà utilisé, mot de passe refusé...) ou serveur injoignable
        setError(messageErreur(err))
      }
    } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:p-4">
      <div className="absolute inset-0 bg-navy-900/70 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white rounded-t-3xl sm:rounded-3xl shadow-2xl w-full sm:max-w-md animate-slide-in overflow-hidden max-h-[92vh] overflow-y-auto">

        <div className="px-6 sm:px-8 pt-7 pb-6 bg-navy-700">
          <button onClick={onClose} aria-label="Fermer"
            className="absolute top-4 right-4 p-1.5 rounded-lg text-white/70 hover:text-white hover:bg-white/10">
            <FiX className="w-5 h-5" />
          </button>
          <h2 className="text-white font-display text-3xl font-bold">
            {mode === 'login' ? 'Connexion' : 'Creer un compte'}
          </h2>
          <p className="text-white/70 text-sm mt-1">
            {mode === 'login'
              ? 'Acces a votre espace securise'
              : 'Rejoignez SunuTribunal'
            }
          </p>
        </div>

        <div className="px-6 sm:px-8 py-6">
          {error && (
            <div className="flex items-center gap-2 bg-danger-50 border border-danger-100 text-danger-600 rounded-xl px-4 py-3 mb-4 text-sm">
              <FiAlertCircle className="w-4 h-4 flex-shrink-0" />{error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="form-label">Nom *</label>
                  <input className="form-input" placeholder="Diallo"
                    value={form.nom} onChange={e => set('nom', e.target.value)} />
                </div>
                <div>
                  <label className="form-label">Prenom</label>
                  <input className="form-input" placeholder="Abdoulaye"
                    value={form.prenom} onChange={e => set('prenom', e.target.value)} />
                </div>
              </div>
            )}

            <div>
              <label className="form-label">Adresse email</label>
              <div className="relative">
                <FiMailIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input className="form-input pl-10" type="email" required
                  placeholder="votre@email.sn" autoComplete="email"
                  value={form.email} onChange={e => set('email', e.target.value)} />
              </div>
            </div>

            {mode === 'register' && (
              <div>
                <label className="form-label">Telephone</label>
                <input className="form-input" placeholder="+221 77 000 00 00"
                  value={form.telephone} onChange={e => set('telephone', e.target.value)} />
              </div>
            )}

            <div>
              <label className="form-label">Mot de passe</label>
              <div className="relative">
                <FiLock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input className="form-input pl-10 pr-10"
                  type={showPass ? 'text' : 'password'} required placeholder="••••••••" minLength={6}
                  value={form.password} onChange={e => set('password', e.target.value)} />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  aria-label={showPass ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-navy-700">
                  {showPass ? <FiEyeOff className="w-4 h-4" /> : <FiEye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading}
              className={`w-full py-3 btn-primary ${loading ? 'cursor-wait' : ''}`}>
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {mode === 'login' ? 'Connexion...' : 'Creation...'}
                </span>
              ) : (mode === 'login' ? 'Se connecter' : 'Creer mon compte')}
            </button>
          </form>

          {/* Inscription publique : citoyens uniquement (rôle forcé côté serveur) */}
          <div className="mt-5 text-center">
            <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-gray-500 hover:text-navy-700 transition-colors">
              {mode === 'login'
                ? <>Pas encore de compte ? <span className="font-semibold text-justice-500">Creer un compte</span></>
                : <>Deja inscrit ? <span className="font-semibold text-justice-500">Se connecter</span></>}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── CONTENU DE LA PAGE ─────────────────────────────
const SERVICES = [
  { icon: FiCalendar,      titre: 'Rendez-vous',            desc: 'Reservez un creneau au tribunal, sans file d\'attente.' },
  { icon: FiFileText,      titre: 'Plainte en ligne',       desc: 'Deposez votre plainte avec vos pieces scannees.' },
  { icon: FiSearch,        titre: 'Suivi de dossier',       desc: 'Suivez chaque etape de votre procedure en direct.' },
  { icon: FiMapPin,        titre: 'Carte des tribunaux',    desc: 'Trouvez le tribunal le plus proche de chez vous.' },
  { icon: FiAlertTriangle, titre: 'Alerte SOS',             desc: 'Signalez une urgence avec votre position GPS.', sos: true },
  { icon: FiMessageCircle, titre: 'Assistant juridique IA', desc: 'Posez vos questions de droit, a toute heure.' },
]

const ETAPES = [
  { icon: FiUserPlus,   titre: 'Je cree mon compte',     desc: 'Email et telephone : c\'est gratuit et immediat.' },
  { icon: FiSend,       titre: 'Je fais ma demarche',    desc: 'Rendez-vous, plainte ou courrier, depuis mon telephone.' },
  { icon: FiSmartphone, titre: 'Je recois un SMS',       desc: 'Le tribunal me repond : confirmation, orientation, decision.' },
]

export default function LandingPage() {
  const [showAuthModal, setShowAuthModal]   = useState(false)
  const [authMode, setAuthMode]             = useState('login')
  const [mobileMenu, setMobileMenu]         = useState(false)
  const [scrolled, setScrolled]             = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 40)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  // La redirection "deja connecte" est geree une seule fois dans App.jsx (route "/")

  const ouvrirAuth = (mode = 'login') => {
    setMobileMenu(false)
    setAuthMode(mode)
    setShowAuthModal(true)
  }
  const openLogin    = () => ouvrirAuth('login')
  const openRegister = () => ouvrirAuth('register')   // inscription : citoyens uniquement

  const lienNav = 'text-sm font-medium text-white/80 hover:text-white transition-colors'

  return (
    <div className="min-h-screen bg-gray-50 font-body">

      {/* ── NAVBAR : transparente sur la bannière, Encre au défilement ── */}
      <nav className={`fixed top-0 inset-x-0 z-40 transition-all duration-300 ${
        scrolled || mobileMenu ? 'bg-navy-700/95 backdrop-blur shadow-[0_1px_0_rgba(255,255,255,0.06)]' : 'bg-transparent'
      }`}>
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 md:h-20 flex items-center justify-between">
          <a href="#haut" aria-label="SunuTribunal — accueil"><Logo fond="sombre" size="sm" /></a>

          <div className="hidden md:flex items-center gap-8">
            <a href="#services" className={lienNav}>Nos services</a>
            <a href="#comment" className={lienNav}>Comment ca marche</a>
          </div>

          <div className="hidden md:flex items-center gap-2">
            <button onClick={openLogin} className="text-sm font-semibold text-white px-4 py-2 rounded-xl hover:bg-white/10 transition-colors">
              Se connecter
            </button>
            <button onClick={openRegister}
              className="text-sm font-semibold text-white px-4 py-2 rounded-xl border border-white/40 hover:border-white hover:bg-white/5 transition-colors">
              Creer un compte
            </button>
          </div>

          <button className="md:hidden p-2 -mr-2 text-white" onClick={() => setMobileMenu(!mobileMenu)}
            aria-label={mobileMenu ? 'Fermer le menu' : 'Ouvrir le menu'} aria-expanded={mobileMenu}>
            {mobileMenu ? <FiX className="w-6 h-6" /> : <FiMenu className="w-6 h-6" />}
          </button>
        </div>

        {mobileMenu && (
          <div className="md:hidden border-t border-white/10 px-4 pb-5 pt-2 space-y-1 animate-fade-in">
            <a href="#services" onClick={() => setMobileMenu(false)} className="block text-white/85 py-3 text-[15px]">Nos services</a>
            <a href="#comment" onClick={() => setMobileMenu(false)} className="block text-white/85 py-3 text-[15px]">Comment ca marche</a>
            <div className="grid grid-cols-2 gap-3 pt-3">
              <button onClick={openLogin} className="py-3 rounded-xl border border-white/40 text-white text-sm font-semibold">
                Se connecter
              </button>
              <button onClick={openRegister} className="py-3 rounded-xl bg-white text-navy-700 text-sm font-semibold">
                Creer un compte
              </button>
            </div>
          </div>
        )}
      </nav>

      {/* ── BANNIÈRE ── */}
      <header id="haut" className="relative min-h-[100svh] flex overflow-hidden bg-navy-700">
        {/* Mobile < 768 px : image portrait · écrans moyens : 1600 px · grands écrans : 2400 px */}
        <picture>
          <source media="(max-width: 767px)" srcSet={heroMobile} />
          <source media="(max-width: 1600px)" srcSet={hero1600} />
          <img src={heroDesktop} alt="" aria-hidden="true"
            className="absolute inset-0 w-full h-full object-cover object-[center_top] md:object-[right_center]" />
        </picture>
        {/* Dégradé Encre (#070D17) : bas sombre sur mobile (texte en bas), gauche sombre sur ordinateur */}
        <div className="absolute inset-0 md:hidden"
          style={{ background: 'linear-gradient(to top, rgba(7,13,23,0.96) 0%, rgba(7,13,23,0.80) 34%, rgba(7,13,23,0.15) 62%, rgba(7,13,23,0.45) 100%)' }} />
        <div className="absolute inset-0 hidden md:block"
          style={{ background: 'linear-gradient(to right, rgba(7,13,23,0.90) 0%, rgba(7,13,23,0.60) 35%, rgba(7,13,23,0.05) 62%)' }} />

        <div className="relative w-full max-w-6xl mx-auto px-5 sm:px-6 pt-28 pb-12 md:py-0 flex items-end md:items-center">
          <div className="max-w-xl">
            <p className="text-white/70 text-xs font-semibold uppercase tracking-[0.2em] mb-4">
              Justice digitale · Senegal
            </p>
            <h1 className="font-display text-white font-bold leading-[1.05] text-[2.6rem] sm:text-5xl lg:text-[4.25rem]">
              La justice,<br />plus proche de vous.
            </h1>
            <p className="text-white/80 text-base md:text-lg leading-relaxed mt-5 max-w-md">
              Rendez-vous, plainte, suivi de dossier et alerte SOS : vos demarches au tribunal,
              depuis votre telephone.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mt-8">
              <button onClick={openLogin} className="btn-gold py-3.5 px-7 text-[15px]">
                <FiCalendar className="w-4 h-4 mr-2" /> Prendre rendez-vous
              </button>
              <button onClick={openLogin}
                className="inline-flex items-center justify-center py-3.5 px-7 rounded-xl border border-white/70 text-white text-[15px] font-semibold hover:bg-white/10 hover:border-white transition-all">
                <FiLogIn className="w-4 h-4 mr-2" /> Se connecter
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── NOS SERVICES ── */}
      <section id="services" className="py-20 md:py-28 scroll-mt-16">
        <div className="max-w-6xl mx-auto px-5 sm:px-6">
          <div className="max-w-xl mb-10 md:mb-14">
            <p className="text-justice-500 text-xs font-semibold uppercase tracking-[0.18em] mb-3">Nos services</p>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-navy-700 leading-tight">
              Tout le tribunal, dans votre poche
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-5">
            {SERVICES.map(s => (
              <button key={s.titre} onClick={openLogin}
                className="card text-left flex items-start gap-4 hover:-translate-y-0.5 group">
                <span className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${
                  s.sos ? 'bg-danger-50 text-danger-400' : 'bg-navy-50 text-navy-700'
                }`}>
                  <s.icon className="w-5 h-5" />
                </span>
                <span>
                  <span className="block font-semibold text-navy-700">{s.titre}</span>
                  <span className="block text-sm text-gray-500 mt-1 leading-relaxed">{s.desc}</span>
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ── COMMENT ÇA MARCHE ── */}
      <section id="comment" className="py-20 md:py-28 bg-white border-y border-gray-200 scroll-mt-16">
        <div className="max-w-6xl mx-auto px-5 sm:px-6">
          <div className="max-w-xl mb-10 md:mb-14">
            <p className="text-justice-500 text-xs font-semibold uppercase tracking-[0.18em] mb-3">Comment ca marche</p>
            <h2 className="font-display text-4xl md:text-5xl font-bold text-navy-700 leading-tight">
              Trois etapes, c'est tout
            </h2>
          </div>
          <ol className="grid md:grid-cols-3 gap-8 md:gap-10">
            {ETAPES.map((e, i) => (
              <li key={e.titre} className="relative">
                <div className="flex items-center gap-4 mb-4">
                  <span className="font-display text-5xl font-bold text-navy-100 leading-none">0{i + 1}</span>
                  <span className="w-10 h-10 rounded-full bg-navy-700 text-white flex items-center justify-center">
                    <e.icon className="w-4 h-4" />
                  </span>
                </div>
                <h3 className="font-display text-2xl font-bold text-navy-700">{e.titre}</h3>
                <p className="text-gray-500 mt-2 leading-relaxed">{e.desc}</p>
              </li>
            ))}
          </ol>
          <button onClick={openRegister} className="btn-primary mt-12 py-3 px-6">
            Creer mon compte citoyen <FiArrowRight className="w-4 h-4 ml-2" />
          </button>
        </div>
      </section>

      {/* ── PIED DE PAGE ── */}
      <footer className="bg-navy-700 text-white">
        <div className="max-w-6xl mx-auto px-5 sm:px-6 py-12">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-8">
            <Logo fond="sombre" size="md" />
            <nav className="flex flex-wrap gap-x-7 gap-y-3 text-sm text-white/75" aria-label="Liens du pied de page">
              <a href="#services" className="hover:text-white transition-colors">Nos services</a>
              <a href="#comment" className="hover:text-white transition-colors">Comment ca marche</a>
              <button onClick={openLogin} className="hover:text-white transition-colors">Se connecter</button>
              <button onClick={openRegister} className="hover:text-white transition-colors">Creer un compte</button>
            </nav>
          </div>
          <div className="border-t border-white/10 mt-10 pt-6 flex flex-col sm:flex-row sm:justify-between gap-2 text-xs text-white/60">
            <p>Ministere de la Justice — Republique du Senegal</p>
            <p>© {new Date().getFullYear()} SunuTribunal · Justice digitale</p>
          </div>
        </div>
      </footer>

      {/* ── MODALS ── */}
      {showAuthModal && (
        <AuthModal
          mode={authMode}
          onClose={() => setShowAuthModal(false)}
        />
      )}
    </div>
  )
}
