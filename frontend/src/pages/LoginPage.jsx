import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FiLock, FiMail, FiShield, FiEye, FiEyeOff, FiAlertCircle } from 'react-icons/fi'
import { useAuth, ROLES } from '../context/AuthContext.jsx'
import { authAPI, messageErreur } from '../services/api.js'
import Logo from '../components/common/Logo.jsx'
import toast from 'react-hot-toast'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [role, setRole]         = useState('citoyen')
  const [mode, setMode]         = useState('login')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [form, setForm] = useState({ email:'', password:'', nom:'', prenom:'', telephone:'' })

  const set = (k, v) => { setForm(f => ({...f, [k]: v})); setError('') }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!form.email || !form.password) { setError('Veuillez remplir tous les champs.'); return }
    setLoading(true)
    try {
      if (mode === 'login') {
        const res = await authAPI.login({ email: form.email, password: form.password })
        const { access, user } = res.data
        login(user, access)
        toast.success('Bienvenue ' + user.nom + ' !')
        navigate(user.role === 'admin' || user.role === 'juge' ? '/admin' : '/citoyen')
      } else {
        if (!form.nom) { setError('Le nom est requis.'); setLoading(false); return }
        await authAPI.register({
          email: form.email, password: form.password,
          password2: form.password, nom: form.nom,
          prenom: form.prenom, telephone: form.telephone,
          role: role === 'admin' ? 'admin' : 'citoyen',
        })
        toast.success('Compte cree ! Connectez-vous.')
        setMode('login')
        setForm(f => ({...f, password:''}))
      }
    } catch (err) {
      if (mode === 'login' && err.response?.status === 401) {
        // Identifiants refusés (ou compte bloqué) : message unique du serveur, sans détail sur le compte
        setError(err.response.data?.detail || 'Email ou mot de passe incorrect.')
      } else {
        // Inscription (email déjà utilisé, mot de passe refusé...) ou serveur injoignable
        setError(messageErreur(err))
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy-700 via-navy-600 to-navy-500 flex">
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative overflow-hidden">
        <div className="absolute inset-0 opacity-5"
          style={{ backgroundImage: 'radial-gradient(circle at 20% 80%, #C9A45C 0%, transparent 50%)' }} />
        <Logo fond="sombre" size="lg" />
        <div>
          <h1 className="font-display text-4xl font-bold text-white mb-4 leading-tight">
            Une justice moderne<br />pour tous les Senegalais
          </h1>
          <p className="text-white/60 text-lg leading-relaxed mb-8">
            Acces a vos droits, gestion de dossiers et justice depuis votre telephone.
          </p>
          <div className="grid grid-cols-2 gap-4">
            {[
              { val:'Rendez-vous en ligne', sub:'Sans file attente'   },
              { val:'Plaintes digitales',   sub:'Avec pieces jointes' },
              { val:'Suivi temps reel',     sub:'Notifications push'  },
              { val:'Alerte SOS GPS',       sub:'Reponse immediate'   },
            ].map(s => (
              <div key={s.val} className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
                <div className="text-white font-semibold text-sm">{s.val}</div>
                <div className="text-white/50 text-xs mt-0.5">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
        <p className="text-white/30 text-sm">2025 SunuTribunal · Ministere de la Justice · Senegal</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6">
        <div className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md animate-slide-in">
          <div className="lg:hidden flex justify-center mb-6"><Logo size="lg" /></div>
          <h2 className="font-display text-2xl font-bold text-navy-700 mb-1">
            {mode === 'login' ? 'Connexion' : 'Creer un compte'}
          </h2>
          <p className="text-gray-500 text-sm mb-6">
            {mode === 'login' ? 'Acces a votre espace securise' : 'Rejoignez SunuTribunal'}
          </p>

          <div className="flex bg-gray-100 rounded-2xl p-1 mb-6">
            {[{ key:'citoyen', label:'Citoyen' }, { key:'admin', label:'Tribunal' }].map(r => (
              <button key={r.key} onClick={() => { setRole(r.key); setError('') }}
                className={`flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all duration-200 ${
                  role === r.key
                    ? r.key === 'admin' ? 'bg-navy-700 text-white shadow-sm' : 'bg-justice-500 text-white shadow-sm'
                    : 'text-gray-500 hover:text-gray-700'
                }`}>{r.label}</button>
            ))}
          </div>

          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 mb-4 text-sm">
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
              <label className="form-label">{role === 'admin' ? 'Identifiant judiciaire' : 'Adresse email'}</label>
              <div className="relative">
                <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input className="form-input pl-10" type="email" required
                  placeholder={role === 'admin' ? 'greffier@tgi-dakar.sn' : 'votre@email.sn'}
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
                <FiLock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                <input className="form-input pl-10 pr-10"
                  type={showPass ? 'text' : 'password'} required placeholder="••••••••" minLength={6}
                  value={form.password} onChange={e => set('password', e.target.value)} />
                <button type="button" onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                  {showPass ? <FiEyeOff className="w-4 h-4" /> : <FiEye className="w-4 h-4" />}
                </button>
              </div>
            </div>
            {role === 'admin' && (
              <div className="flex items-center gap-2 bg-navy-50 rounded-xl p-3 text-xs text-navy-600">
                <FiShield className="w-4 h-4 flex-shrink-0" />
                Acces reserve au personnel judiciaire accredite
              </div>
            )}
            <button type="submit" disabled={loading}
              className={`w-full py-3 rounded-xl font-bold text-white transition-all duration-200 ${
                loading ? 'opacity-70 cursor-wait' : 'active:scale-95'
              } ${role === 'admin' ? 'bg-navy-700 hover:bg-navy-600' : 'bg-justice-500 hover:bg-justice-400'}`}>
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  {mode === 'login' ? 'Connexion...' : 'Creation...'}
                </span>
              ) : (mode === 'login' ? 'Se connecter' : 'Creer mon compte')}
            </button>
          </form>

          <div className="mt-5 text-center">
            <button onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}
              className="text-sm text-gray-500 hover:text-navy-700 transition-colors">
              {mode === 'login' ? 'Pas encore de compte ? Creer un compte' : 'Deja inscrit ? Se connecter'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}