import { useState, useEffect } from 'react'
import { FiShield, FiPlus, FiTrash2, FiAlertCircle, FiCheck, FiMail, FiPhone, FiSend, FiKey } from 'react-icons/fi'
import { staffAPI, messageErreur } from '../../services/api.js'
import { useAuth } from '../../context/AuthContext.jsx'
import toast from 'react-hot-toast'

const ROLES = [
  { value: 'admin',     label: 'Greffier en chef',  desc: 'Acces complet — gestion de tous les dossiers'     },
  { value: 'juge',      label: 'Juge',               desc: 'Instruction et decision sur les dossiers'         },
  { value: 'greffier',  label: 'Greffier',           desc: 'Gestion des plaintes, registres et archives'      },
  { value: 'accueil',   label: 'Accueil / orientation', desc: 'Validation des RDV, orientation des usagers'   },
  { value: 'courrier',  label: 'Bureau courrier',    desc: 'Registres arrivee / depart et transmission'       },
]
// Le greffier en chef se cree uniquement dans l'administration Django (par le superutilisateur)
const ROLES_CREABLES = ROLES.filter(r => r.value !== 'admin')

// Convertit un utilisateur renvoye par l'API au format de l'affichage
const versAffichage = (u) => ({
  id:     u.id,
  nom:    u.nom || '',
  prenom: u.prenom || '',
  email:  u.email,
  role:   u.role,
  actif:  u.is_active,
  doitChanger: !!u.doit_changer_mdp,
  date:   new Date(u.date_joined).toLocaleDateString('fr-FR', { day:'2-digit', month:'short', year:'numeric' }),
})

const FORM_VIDE = { nom:'', prenom:'', email:'', telephone:'', role:'greffier' }

export default function AdminUtilisateurs() {
  const { user } = useAuth()
  const estChef = user?.role === 'admin'

  const [utilisateurs, setUtilisateurs] = useState([])
  const [chargement, setChargement]     = useState(true)
  const [showForm, setShowForm]         = useState(false)
  const [loading, setLoading]           = useState(false)
  const [error, setError]               = useState('')
  const [success, setSuccess]           = useState(null)   // { message, emailEnvoye }
  const [renvoiEnCours, setRenvoiEnCours] = useState(null)
  const [form, setForm] = useState(FORM_VIDE)

  // Chargement du personnel depuis le backend
  useEffect(() => {
    if (!estChef) { setChargement(false); return }
    staffAPI.list()
      .then(res => setUtilisateurs(res.data.map(versAffichage)))
      .catch(err => toast.error(messageErreur(err, 'Impossible de charger le personnel.')))
      .finally(() => setChargement(false))
  }, [estChef])

  const set = (k, v) => { setForm(f => ({...f, [k]: v})); setError('') }

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!form.nom || !form.email) {
      setError('Veuillez remplir tous les champs obligatoires.')
      return
    }
    setLoading(true)
    setError('')
    try {
      // Aucun mot de passe : le serveur en génère un et l'envoie par e-mail à l'agent
      const res = await staffAPI.create({
        email:     form.email,
        nom:       form.nom,
        prenom:    form.prenom,
        telephone: form.telephone,
        role:      form.role,
      })
      setUtilisateurs(u => [versAffichage(res.data), ...u])
      setSuccess({ message: res.data.message, emailEnvoye: res.data.email_envoye })
      if (res.data.email_envoye) toast.success(res.data.message)
      else toast.error(res.data.message, { duration: 8000 })
      setForm(FORM_VIDE)
    } catch (err) {
      setError(messageErreur(err, 'Erreur lors de la creation du compte.'))
    } finally {
      setLoading(false)
    }
  }

  const renvoyer = async (u) => {
    const ok = window.confirm(
      `Renvoyer les identifiants à ${u.prenom} ${u.nom} ?\n\n` +
      `Un NOUVEAU mot de passe provisoire sera envoyé à ${u.email}. ` +
      `L'ancien ne fonctionnera plus et l'agent devra le changer à sa prochaine connexion.`)
    if (!ok) return
    setRenvoiEnCours(u.id)
    try {
      const res = await staffAPI.renvoyer(u.id)
      // Si l'e-mail n'est pas parti, l'ancien mot de passe reste valable : rien ne change pour l'agent
      if (res.data.email_envoye) {
        setUtilisateurs(liste => liste.map(x => x.id === u.id ? { ...x, doitChanger: true } : x))
        toast.success(res.data.message)
      } else {
        toast.error(res.data.message, { duration: 8000 })
      }
    } catch (err) {
      toast.error(messageErreur(err, "Impossible de renvoyer les identifiants."))
    } finally {
      setRenvoiEnCours(null)
    }
  }

  const desactiver = async (id) => {
    const cible = utilisateurs.find(x => x.id === id)
    if (!cible) return
    try {
      await staffAPI.update(id, { is_active: !cible.actif })
      setUtilisateurs(u => u.map(x => x.id === id ? {...x, actif: !x.actif} : x))
      toast.success(cible.actif ? 'Compte desactive' : 'Compte reactive')
    } catch (err) {
      toast.error(messageErreur(err, 'Mise a jour impossible.'))
    }
  }

  const getRoleStyle = (role) => {
    switch(role) {
      case 'admin':    return 'bg-red-50 text-red-700 border-red-200'
      case 'juge':     return 'bg-navy-50 text-navy-700 border-navy-200'
      case 'greffier': return 'bg-justice-50 text-justice-700 border-justice-200'
      case 'accueil':  return 'bg-gold-50 text-gold-500 border-gold-100'
      case 'courrier': return 'bg-amber-50 text-amber-700 border-amber-200'
      default:         return 'bg-gray-50 text-gray-700 border-gray-200'
    }
  }

  const getRoleLabel = (role) => {
    return ROLES.find(r => r.value === role)?.label || role
  }

  if (!estChef) {
    return (
      <div className="p-4 lg:p-6">
        <div className="card max-w-lg mx-auto text-center py-10">
          <div className="w-16 h-16 rounded-full bg-navy-50 flex items-center justify-center mx-auto mb-4">
            <FiShield className="w-8 h-8 text-navy-700" />
          </div>
          <p className="font-bold text-navy-700 text-lg">Acces reserve au greffier en chef</p>
          <p className="text-gray-500 text-sm mt-1">
            Seul le greffier en chef peut creer ou desactiver les comptes du personnel judiciaire.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="p-4 lg:p-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-700">Personnel judiciaire</h1>
          <p className="text-gray-500 text-sm mt-1">Gestion des comptes du tribunal</p>
        </div>
        <button onClick={() => { setShowForm(!showForm); setError(''); setSuccess(null) }}
          className="btn-primary flex items-center gap-2 whitespace-nowrap flex-shrink-0 px-4">
          <FiPlus className="w-4 h-4" />
          Creer un compte
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        {[
          { label:'Total personnel',  num: utilisateurs.length,                           color:'text-navy-700'    },
          { label:'Comptes actifs',   num: utilisateurs.filter(u => u.actif).length,      color:'text-justice-500' },
          { label:'Roles differents', num: [...new Set(utilisateurs.map(u=>u.role))].length, color:'text-gold-500' },
        ].map(s => (
          <div key={s.label} className="card text-center">
            <div className={`text-3xl font-display font-bold ${s.color}`}>{s.num}</div>
            <div className="text-xs text-gray-500 mt-1 uppercase tracking-wide">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Formulaire creation */}
      {showForm && (
        <div className="card mb-6 border-2 border-navy-100">
          <h3 className="font-semibold text-navy-700 mb-5 flex items-center gap-2">
            <FiShield className="w-4 h-4 text-gold-500" />
            Creer un nouveau compte judiciaire
          </h3>

          {success ? (
            <div className="flex flex-col items-center py-8 text-center">
              <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-4 ${
                success.emailEnvoye ? 'bg-justice-50' : 'bg-amber-50'}`}>
                {success.emailEnvoye
                  ? <FiCheck className="w-8 h-8 text-justice-500" />
                  : <FiAlertCircle className="w-8 h-8 text-amber-600" />}
              </div>
              <p className="font-bold text-navy-700 text-lg">
                {success.emailEnvoye ? 'Compte créé' : 'Compte créé, e-mail non envoyé'}
              </p>
              <p className="text-gray-600 text-sm mt-1 max-w-md">{success.message}</p>
              <div className="flex gap-3 mt-6">
                <button type="button" className="btn-ghost" onClick={() => { setShowForm(false); setSuccess(null) }}>
                  Fermer
                </button>
                <button type="button" className="btn-primary" onClick={() => setSuccess(null)}>
                  <FiPlus className="w-4 h-4 mr-2" /> Créer un autre compte
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={handleCreate} className="space-y-4">
              {error && (
                <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
                  <FiAlertCircle className="w-4 h-4 flex-shrink-0" />{error}
                </div>
              )}

              {/* Role */}
              <div>
                <label className="form-label">Role * </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2">
                  {ROLES_CREABLES.map(r => (
                    <button key={r.value} type="button"
                      onClick={() => set('role', r.value)}
                      className={`p-3 rounded-xl border-2 text-left transition-all ${
                        form.role === r.value
                          ? 'border-navy-700 bg-navy-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}>
                      <p className="font-bold text-sm text-navy-700">{r.label}</p>
                      <p className="text-xs text-gray-500 mt-0.5 leading-tight">{r.desc}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Nom Prenom */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="form-label">Nom *</label>
                  <input className="form-input" placeholder="Sarr"
                    value={form.nom} onChange={e => set('nom', e.target.value)} required />
                </div>
                <div>
                  <label className="form-label">Prenom</label>
                  <input className="form-input" placeholder="Fatou"
                    value={form.prenom} onChange={e => set('prenom', e.target.value)} />
                </div>
              </div>

              {/* Email */}
              <div>
                <label className="form-label">Email judiciaire *</label>
                <div className="relative">
                  <FiMail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input className="form-input pl-10" type="email" required
                    placeholder="greffier@tgi-dakar.sn"
                    value={form.email} onChange={e => set('email', e.target.value)} />
                </div>
              </div>

              {/* Telephone */}
              <div>
                <label className="form-label">Telephone</label>
                <div className="relative">
                  <FiPhone className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 w-4 h-4" />
                  <input className="form-input pl-10" placeholder="+221 77 000 00 00"
                    value={form.telephone} onChange={e => set('telephone', e.target.value)} />
                </div>
              </div>

              {/* Plus de mot de passe à saisir : il est généré et envoyé par e-mail */}
              <div className="flex items-start gap-3 bg-navy-50 border border-navy-100 rounded-xl p-3 text-xs text-navy-600 leading-relaxed">
                <FiKey className="w-4 h-4 flex-shrink-0 mt-0.5" />
                <span>
                  Un <strong>mot de passe provisoire</strong> sera généré automatiquement et envoyé à l'adresse
                  e-mail ci-dessus. L'agent devra le remplacer par le sien dès sa première connexion.
                  Le compte sera rattaché à votre juridiction.
                </span>
              </div>

              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => { setShowForm(false); setError('') }}
                  className="btn-ghost flex-1">
                  Annuler
                </button>
                <button type="submit" disabled={loading}
                  className="btn-primary flex-1 flex items-center justify-center gap-2">
                  {loading
                    ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    : <FiPlus className="w-4 h-4" />
                  }
                  {loading ? 'Creation...' : 'Creer le compte'}
                </button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Liste utilisateurs */}
      <div className="card">
        <h3 className="font-semibold text-navy-700 mb-4">
          Personnel enregistre ({utilisateurs.length})
        </h3>
        <div className="space-y-3">
          {chargement && (
            <div className="flex justify-center py-8">
              <span className="w-6 h-6 border-2 border-navy-100 border-t-navy-700 rounded-full animate-spin" />
            </div>
          )}
          {!chargement && utilisateurs.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-6">Aucun compte du personnel pour le moment.</p>
          )}
          {utilisateurs.map(u => (
            <div key={u.id}
              className={`flex items-center gap-4 p-4 rounded-xl border transition-all ${
                u.actif ? 'bg-gray-50 border-gray-200' : 'bg-red-50 border-red-100 opacity-60'
              }`}>

              <div className="w-10 h-10 rounded-full bg-navy-700 flex items-center justify-center text-white font-bold text-sm flex-shrink-0">
                {u.nom?.[0] || ''}{u.prenom?.[0] || ''}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold text-navy-700 text-sm">
                    {u.prenom} {u.nom}
                  </p>
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${getRoleStyle(u.role)}`}>
                    {getRoleLabel(u.role)}
                  </span>
                  {!u.actif && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-600 border border-red-200">
                      Desactive
                    </span>
                  )}
                  {u.actif && u.doitChanger && (
                    <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-amber-50 text-amber-800 border border-amber-200">
                      Mot de passe à définir
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-0.5">{u.email}</p>
                <p className="text-xs text-gray-400">Compte cree le {u.date}</p>
              </div>

              {u.role !== 'admin' && (
              <div className="flex items-center gap-2 flex-shrink-0">
                {u.actif && (
                  <button onClick={() => renvoyer(u)} disabled={renvoiEnCours === u.id}
                    title="Renvoyer les identifiants" aria-label={`Renvoyer les identifiants à ${u.prenom} ${u.nom}`}
                    className="p-2 rounded-xl text-navy-600 hover:bg-navy-50 transition-colors disabled:opacity-50">
                    {renvoiEnCours === u.id
                      ? <span className="block w-4 h-4 border-2 border-navy-100 border-t-navy-700 rounded-full animate-spin" />
                      : <FiSend className="w-4 h-4" />}
                  </button>
                )}
                <button onClick={() => desactiver(u.id)}
                  title={u.actif ? 'Desactiver' : 'Reactiver'}
                  className={`p-2 rounded-xl transition-colors ${
                    u.actif
                      ? 'text-red-500 hover:bg-red-50'
                      : 'text-justice-500 hover:bg-justice-50'
                  }`}>
                  {u.actif
                    ? <FiTrash2 className="w-4 h-4" />
                    : <FiCheck className="w-4 h-4" />
                  }
                </button>
              </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}