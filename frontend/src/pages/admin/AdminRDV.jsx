import { useState, useEffect, useCallback } from 'react'
import { FiCheck, FiX, FiClock, FiMessageSquare, FiUserCheck, FiRefreshCw } from 'react-icons/fi'
import Badge from '../../components/common/Badge.jsx'
import toast from 'react-hot-toast'
import { rdvAPI, smsAPI, messageErreur } from '../../services/api.js'
import usePolling from '../../hooks/usePolling.js'
import { useCompteurs } from '../../context/CompteursContext.jsx'

const CRENEAUX = ['08:00', '09:00', '10:00', '11:00', '14:00', '15:00', '16:00']

const STATUT_BADGE = {
  pending:   { status: 'pending',  label: 'En attente' },
  confirmed: { status: 'progress', label: 'Confirme'   },
  done:      { status: 'done',     label: 'Effectue'   },
  rejected:  { status: 'rejected', label: 'Rejete'     },
  cancelled: { status: 'rejected', label: 'Annule'     },
}

const SMS_BADGE = {
  envoye:          { status: 'done',     label: 'Envoye'         },
  echec:           { status: 'urgent',   label: 'Echec'          },
  non_configure:   { status: 'pending',  label: 'Non configure'  },
  numero_invalide: { status: 'rejected', label: 'N° invalide'    },
}

const aujourdhuiISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
const fmtDate  = (d) => new Date(d + 'T00:00').toLocaleDateString('fr-FR')
const fmtHeure = (h) => h?.slice(0, 5).replace(':', 'h')

// Message affiché après une décision, selon le résultat de l'envoi SMS
function annoncerSMS(res, action) {
  const { sms, sms_erreur } = res.data
  if (sms === 'envoye') toast.success(`RDV ${action} — SMS envoye au citoyen`)
  else if (sms === 'non_configure') toast(`RDV ${action}. SMS non envoye : Twilio n'est pas configure.`, { icon: '⚠️' })
  else if (sms === 'numero_invalide') toast(`RDV ${action}. Le citoyen n'a pas de numero valide pour le SMS.`, { icon: '⚠️' })
  else toast.error(`RDV ${action}, mais le SMS a echoue : ${sms_erreur || 'erreur du service SMS'}`)
}

export default function AdminRDV() {
  const [rdvs, setRdvs]         = useState([])
  const [sms, setSms]           = useState([])
  const [chargement, setChargement] = useState(true)
  const [filtre, setFiltre]     = useState('')
  const [enCours, setEnCours]   = useState(null)
  const [motifModal, setMotifModal] = useState(null)
  const [motifTexte, setMotifTexte] = useState('')

  const { rafraichirCompteurs } = useCompteurs()

  const charger = useCallback(async (auto = false) => {
    try {
      const [r, s] = await Promise.all([rdvAPI.list(), smsAPI.list().catch(() => ({ data: [] }))])
      setRdvs(r.data)
      setSms(s.data)
      if (!auto) rafraichirCompteurs()
    } catch (err) {
      if (!auto) toast.error(messageErreur(err, 'Impossible de charger les rendez-vous.'))
    } finally {
      setChargement(false)
    }
  }, [rafraichirCompteurs])

  // Nouvelles demandes des citoyens : rafraîchissement automatique toutes les 15 s
  usePolling(charger)

  const valider = async (id) => {
    setEnCours(id)
    try {
      const res = await rdvAPI.valider(id)
      annoncerSMS(res, 'confirme')
      charger()
    } catch (err) {
      toast.error(messageErreur(err))
    } finally {
      setEnCours(null)
    }
  }

  const rejeter = (id) => {
    setMotifModal(id)
    setMotifTexte('')
  }

  const confirmerRejet = async () => {
    const id = motifModal
    setEnCours(id)
    try {
      const res = await rdvAPI.rejeter(id, motifTexte.trim())
      annoncerSMS(res, 'rejete')
      setMotifModal(null)
      setMotifTexte('')
      charger()
    } catch (err) {
      toast.error(messageErreur(err))
    } finally {
      setEnCours(null)
    }
  }

  const terminer = async (id) => {
    try {
      await rdvAPI.terminer(id)
      toast.success('Presence enregistree')
      charger()
    } catch (err) {
      toast.error(messageErreur(err))
    }
  }

  const jour     = aujourdhuiISO()
  const duJour   = rdvs.filter(r => r.date === jour && !['rejected', 'cancelled'].includes(r.statut))
  const pending  = rdvs.filter(r => r.statut === 'pending')
  const aVenir   = rdvs.filter(r => r.statut === 'confirmed' && r.date >= jour)
  const maintenant = new Date().toTimeString().slice(0, 5)
  const creneaux = CRENEAUX.map(h => ({
    time: h, rdv: duJour.find(r => r.heure?.slice(0, 5) === h), passe: h <= maintenant,
  }))
  const affiches = filtre ? rdvs.filter(r => r.statut === filtre) : rdvs

  const dateTitre = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })

  return (
    <div className="p-4 lg:p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-700">Gestion des rendez-vous</h1>
          <p className="text-gray-500 text-sm mt-1 first-letter:uppercase">{dateTitre}</p>
        </div>
        <button onClick={() => { setChargement(true); charger() }} className="btn-ghost flex items-center gap-2">
          <FiRefreshCw className={`w-4 h-4 ${chargement ? 'animate-spin' : ''}`} />
          <span className="hidden sm:inline">Actualiser</span>
        </button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {[
          { num: duJour.length, label: 'Ce jour' },
          { num: pending.length, label: 'En attente', color: 'text-amber-600' },
          { num: aVenir.length, label: 'Confirmes a venir' },
          { num: creneaux.filter(c => !c.rdv && !c.passe).length, label: 'Creneaux libres' },
        ].map(s => (
          <div key={s.label} className="kpi-box text-center">
            <div className={`kpi-num ${s.color || ''}`}>{s.num}</div>
            <div className="kpi-label text-center">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card mb-6">
        <h3 className="font-semibold text-navy-700 mb-4 flex items-center gap-2">
          <FiClock className="w-4 h-4 text-justice-400" /> Creneaux du jour
        </h3>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {creneaux.map(({ time, rdv, passe }) => {
            const s = !rdv ? (passe ? 'done' : 'free') : rdv.statut === 'done' ? 'done' : rdv.statut === 'pending' ? 'pending' : 'progress'
            return (
              <div key={time} className={`rounded-xl p-3 border ${
                s === 'free' ? 'border-justice-200 bg-justice-50' :
                s === 'done' ? 'bg-gray-50 border-gray-200' :
                s === 'pending' ? 'border-amber-200 bg-amber-50' :
                'border-navy-100 bg-navy-50'
              }`}>
                <p className={`font-bold text-sm ${
                  s === 'free' ? 'text-justice-500' : s === 'pending' ? 'text-amber-700' : 'text-navy-700'
                }`}>{fmtHeure(time)}</p>
                {rdv ? (
                  <>
                    <p className="text-xs text-gray-700 font-medium mt-0.5 truncate">{rdv.citoyen_nom}</p>
                    <p className="text-xs text-gray-400 truncate">{rdv.service_label}</p>
                    <Badge {...STATUT_BADGE[rdv.statut]} className="mt-1.5 text-xs" />
                  </>
                ) : passe ? (
                  <p className="text-xs text-gray-400 font-semibold mt-1">Passe</p>
                ) : (
                  <p className="text-xs text-justice-500 font-semibold mt-1">Disponible</p>
                )}
              </div>
            )
          })}
        </div>
      </div>

      {pending.length > 0 && (
        <div className="card p-0 overflow-hidden overflow-x-auto mb-6">
          <div className="px-5 py-4 border-b border-gray-50 bg-amber-50">
            <h3 className="font-semibold text-amber-700 text-sm uppercase tracking-wide">
              En attente de validation ({pending.length})
            </h3>
          </div>
          <table className="data-table min-w-full">
            <thead><tr><th>Reference</th><th>Citoyen</th><th>Telephone</th><th>Service</th><th>Date</th><th>Heure</th><th>Actions</th></tr></thead>
            <tbody>
              {pending.map(r => (
                <tr key={r.id}>
                  <td className="font-mono text-xs font-semibold text-navy-700">{r.reference}</td>
                  <td className="font-medium">{r.citoyen_nom}</td>
                  <td className="text-xs text-gray-500">{r.citoyen_telephone || <span className="text-red-500">Aucun</span>}</td>
                  <td className="text-gray-500 text-xs">{r.service_label}</td>
                  <td className="text-gray-500 text-xs">{fmtDate(r.date)}</td>
                  <td className="font-semibold text-xs">{fmtHeure(r.heure)}</td>
                  <td>
                    <div className="flex gap-2">
                      <button onClick={() => valider(r.id)} disabled={enCours === r.id}
                        className="flex items-center gap-1 px-3 py-1.5 bg-justice-500 text-white text-xs font-semibold rounded-lg hover:bg-justice-400 transition-colors disabled:opacity-50">
                        {enCours === r.id
                          ? <span className="w-3 h-3 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          : <FiCheck className="w-3 h-3" />} Valider
                      </button>
                      <button onClick={() => rejeter(r.id)} disabled={enCours === r.id}
                        className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white text-xs font-semibold rounded-lg hover:bg-red-500 transition-colors disabled:opacity-50">
                        <FiX className="w-3 h-3" /> Rejeter
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal motif rejet */}
      {motifModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/40" onClick={() => setMotifModal(null)} />
          <div className="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md">
            <h3 className="font-display text-lg font-bold text-navy-700 mb-4">
              Motif du rejet
            </h3>
            <p className="text-sm text-gray-500 mb-3">
              Ce message sera envoye au citoyen par SMS et dans ses notifications.
            </p>
            <textarea
              className="form-input w-full"
              rows={4}
              maxLength={300}
              placeholder="Ex: Creneau indisponible, veuillez choisir une autre date..."
              value={motifTexte}
              onChange={e => setMotifTexte(e.target.value)}
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => setMotifModal(null)}
                className="btn-ghost flex-1">
                Annuler
              </button>
              <button onClick={confirmerRejet} disabled={!motifTexte.trim() || enCours === motifModal}
                className="btn-danger flex-1">
                {enCours === motifModal ? 'Envoi...' : 'Confirmer le rejet'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="card p-0 overflow-hidden overflow-x-auto mb-6">
        <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between gap-3 flex-wrap">
          <h3 className="font-semibold text-navy-700 text-sm uppercase tracking-wide">Tous les rendez-vous</h3>
          <select className="form-select w-auto text-xs py-1.5" value={filtre} onChange={e => setFiltre(e.target.value)}>
            <option value="">Tous les statuts</option>
            {Object.entries(STATUT_BADGE).map(([v, b]) => <option key={v} value={v}>{b.label}</option>)}
          </select>
        </div>
        <table className="data-table min-w-full">
          <thead><tr><th>Reference</th><th>Citoyen</th><th>Service</th><th>Date</th><th>Statut</th><th>Actions</th></tr></thead>
          <tbody>
            {affiches.map(r => (
              <tr key={r.id}>
                <td className="font-mono text-xs font-semibold text-navy-700">{r.reference}</td>
                <td className="font-medium">{r.citoyen_nom}</td>
                <td className="text-gray-500 text-xs">{r.service_label}</td>
                <td className="text-gray-500 text-xs whitespace-nowrap">{fmtDate(r.date)} · {fmtHeure(r.heure)}</td>
                <td>
                  <Badge {...STATUT_BADGE[r.statut]} />
                  {r.statut === 'rejected' && r.motif_rejet && (
                    <p className="text-xs text-gray-400 mt-1 max-w-xs truncate" title={r.motif_rejet}>{r.motif_rejet}</p>
                  )}
                </td>
                <td>
                  {r.statut === 'pending' ? (
                    <div className="flex gap-1">
                      <button onClick={() => valider(r.id)} className="px-2 py-1 bg-justice-500 text-white text-xs rounded-lg"><FiCheck className="w-3 h-3" /></button>
                      <button onClick={() => rejeter(r.id)} className="px-2 py-1 bg-red-600 text-white text-xs rounded-lg"><FiX className="w-3 h-3" /></button>
                    </div>
                  ) : r.statut === 'confirmed' ? (
                    <button onClick={() => terminer(r.id)}
                      className="flex items-center gap-1 text-xs font-semibold text-navy-700 bg-navy-50 px-2.5 py-1.5 rounded-lg hover:bg-navy-100 transition-colors">
                      <FiUserCheck className="w-3.5 h-3.5" /> Present
                    </button>
                  ) : (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!chargement && affiches.length === 0 && (
          <p className="text-center py-8 text-sm text-gray-400">Aucun rendez-vous</p>
        )}
      </div>

      {/* Journal des SMS */}
      <div className="card p-0 overflow-hidden overflow-x-auto">
        <div className="px-5 py-4 border-b border-gray-50">
          <h3 className="font-semibold text-navy-700 text-sm uppercase tracking-wide flex items-center gap-2">
            <FiMessageSquare className="w-4 h-4 text-justice-400" /> Derniers SMS envoyes
          </h3>
        </div>
        <table className="data-table min-w-full">
          <thead><tr><th>Date</th><th>Destinataire</th><th>Numero</th><th>Reference</th><th>Statut</th></tr></thead>
          <tbody>
            {sms.slice(0, 10).map(s => (
              <tr key={s.id} title={s.erreur || s.message}>
                <td className="text-xs text-gray-500 whitespace-nowrap">
                  {new Date(s.created_at).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })}
                </td>
                <td className="text-sm font-medium">{s.destinataire_nom || '—'}</td>
                <td className="text-xs font-mono">{s.telephone || '—'}</td>
                <td className="text-xs font-mono text-navy-700">{s.objet_ref}</td>
                <td><Badge {...(SMS_BADGE[s.statut] || { status: 'pending', label: s.statut_label })} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {sms.length === 0 && <p className="text-center py-6 text-sm text-gray-400">Aucun SMS pour le moment</p>}
      </div>
    </div>
  )
}
