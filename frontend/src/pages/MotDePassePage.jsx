import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { FiLock, FiEye, FiEyeOff, FiCheck, FiLogOut, FiAlertCircle, FiArrowLeft } from 'react-icons/fi'
import Logo from '../components/common/Logo.jsx'
import { authAPI, messageErreur } from '../services/api.js'
import { useAuth, homePathFor } from '../context/AuthContext.jsx'

/** Force du mot de passe (indicatif : le serveur applique les validateurs Django) */
function evaluerForce(mdp) {
  if (!mdp) return { score: 0, libelle: '', couleur: 'bg-gray-200' }
  let score = 0
  if (mdp.length >= 8) score++
  if (mdp.length >= 12) score++
  if (/[a-z]/.test(mdp) && /[A-Z]/.test(mdp)) score++
  if (/\d/.test(mdp)) score++
  if (/[^A-Za-z0-9]/.test(mdp)) score++
  const niveaux = [
    { libelle: 'Très faible', couleur: 'bg-danger-400' },
    { libelle: 'Très faible', couleur: 'bg-danger-400' },
    { libelle: 'Faible',      couleur: 'bg-amber-500' },
    { libelle: 'Moyen',       couleur: 'bg-amber-400' },
    { libelle: 'Bon',         couleur: 'bg-justice-400' },
    { libelle: 'Excellent',   couleur: 'bg-justice-500' },
  ]
  return { score, ...niveaux[score] }
}

/**
 * Changer son mot de passe.
 * - obligatoire : 1re connexion avec le mot de passe provisoire reçu par e-mail ; tant que ce
 *   n'est pas fait, le reste de l'application (et l'API) est bloqué.
 * - sinon : changement volontaire depuis le menu.
 */
export default function MotDePassePage({ obligatoire = false }) {
  const { user, logout, majUtilisateur } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ ancien_mdp: '', nouveau_mdp: '', confirmation: '' })
  const [voir, setVoir] = useState(false)
  const [erreurs, setErreurs] = useState({})
  const [chargement, setChargement] = useState(false)

  const set = (k, v) => { setForm(f => ({ ...f, [k]: v })); setErreurs({}) }
  const accueil = homePathFor(user.role) || '/'
  const force = evaluerForce(form.nouveau_mdp)

  // Règles affichées et vérifiées en direct (le serveur refait toutes les vérifications)
  const regles = [
    { ok: form.nouveau_mdp.length >= 8, texte: '8 caractères minimum' },
    { ok: /[a-z]/.test(form.nouveau_mdp) && /[A-Z]/.test(form.nouveau_mdp), texte: 'Majuscules et minuscules' },
    { ok: /\d/.test(form.nouveau_mdp), texte: 'Au moins un chiffre' },
    { ok: !!form.nouveau_mdp && form.nouveau_mdp !== form.ancien_mdp, texte: "Différent de l'ancien mot de passe" },
    { ok: !!form.nouveau_mdp && form.nouveau_mdp === form.confirmation, texte: 'Confirmation identique' },
  ]
  // Indispensables pour envoyer (les autres règles sont des conseils, la force les reflète)
  const pret = regles[0].ok && regles[3].ok && regles[4].ok && !!form.ancien_mdp

  const enregistrer = async (e) => {
    e.preventDefault()
    setChargement(true)
    try {
      const res = await authAPI.changerMotDePasse(form)
      majUtilisateur({ ...res.data.user, doit_changer_mdp: false })
      toast.success('Mot de passe modifié')
      navigate(accueil, { replace: true })
    } catch (err) {
      const data = err.response?.data
      if (data && typeof data === 'object' && !data.detail) setErreurs(data)
      else toast.error(messageErreur(err))
    } finally {
      setChargement(false)
    }
  }

  const deconnecter = () => { logout(); navigate('/', { replace: true }) }
  const erreur = (champ) => erreurs[champ] && (
    <p className="text-xs text-danger-600 mt-1.5 flex items-start gap-1">
      <FiAlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-px" />
      {[].concat(erreurs[champ]).join(' ')}
    </p>
  )
  const champ = (cle, label, autoComplete) => (
    <div>
      <label className="form-label" htmlFor={cle}>{label}</label>
      <div className="relative">
        <FiLock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
        <input id={cle} className="form-input pl-10" type={voir ? 'text' : 'password'} required
          autoComplete={autoComplete} value={form[cle]} onChange={e => set(cle, e.target.value)}
          aria-invalid={!!erreurs[cle]} />
      </div>
      {erreur(cle)}
    </div>
  )

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center px-4 py-10">
      <Logo size="md" className="mb-8" />
      <div className="card w-full max-w-md p-6 sm:p-8">
        {!obligatoire && (
          <button type="button" onClick={() => (window.history.length > 1 ? navigate(-1) : navigate(accueil))}
            className="text-sm text-gray-500 hover:text-navy-700 flex items-center gap-1.5 mb-4">
            <FiArrowLeft className="w-4 h-4" /> Retour
          </button>
        )}
        <h1 className="font-display text-3xl font-bold text-navy-700">Changer le mot de passe</h1>
        <p className="text-sm text-gray-500 mt-2 leading-relaxed">
          {obligatoire
            ? <>Bonjour {user?.prenom || user?.nom}. Vous vous êtes connecté avec le <strong>mot de passe
                provisoire</strong> reçu par e-mail : choisissez votre mot de passe personnel pour accéder
                à votre espace.</>
            : 'Saisissez votre mot de passe actuel, puis choisissez-en un nouveau.'}
        </p>

        <form onSubmit={enregistrer} className="space-y-4 mt-6">
          {champ('ancien_mdp', obligatoire ? 'Mot de passe provisoire' : 'Mot de passe actuel', 'current-password')}
          {champ('nouveau_mdp', 'Nouveau mot de passe', 'new-password')}

          {/* Indicateur de force */}
          {form.nouveau_mdp && (
            <div aria-live="polite">
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map(i => (
                  <span key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${
                    i <= force.score ? force.couleur : 'bg-gray-200'}`} />
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-1">Force : <strong className="text-navy-700">{force.libelle}</strong></p>
            </div>
          )}

          {champ('confirmation', 'Confirmer le nouveau mot de passe', 'new-password')}

          <button type="button" onClick={() => setVoir(!voir)}
            className="text-xs font-semibold text-gray-500 hover:text-navy-700 flex items-center gap-1.5">
            {voir ? <FiEyeOff className="w-3.5 h-3.5" /> : <FiEye className="w-3.5 h-3.5" />}
            {voir ? 'Masquer les mots de passe' : 'Afficher les mots de passe'}
          </button>

          <ul className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-1.5">
            {regles.map(r => (
              <li key={r.texte} className={`text-xs flex items-center gap-2 ${r.ok ? 'text-justice-600' : 'text-gray-500'}`}>
                <span className={`w-4 h-4 rounded-full flex items-center justify-center flex-shrink-0 ${
                  r.ok ? 'bg-justice-500 text-white' : 'border border-gray-300'}`}>
                  {r.ok && <FiCheck className="w-3 h-3" />}
                </span>
                {r.texte}
              </li>
            ))}
            <li className="text-xs text-gray-500 pl-6">Évitez les mots de passe courants ou proches de votre nom ou e-mail.</li>
          </ul>

          <button type="submit" disabled={chargement || !pret} className="btn-primary w-full py-3">
            {chargement
              ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              : 'Enregistrer le nouveau mot de passe'}
          </button>
        </form>
      </div>
      {obligatoire && (
        <button onClick={deconnecter}
          className="mt-6 text-sm text-gray-500 hover:text-navy-700 flex items-center gap-2">
          <FiLogOut className="w-4 h-4" /> Se déconnecter
        </button>
      )}
    </div>
  )
}
