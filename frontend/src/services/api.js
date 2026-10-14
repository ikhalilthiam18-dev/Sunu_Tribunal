import axios from 'axios'
import { API_BASE, HEADERS_COMMUNS } from '../config.js'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json', ...HEADERS_COMMUNS },
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('st_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Routes où un 401 signifie "mauvais identifiants", PAS "session expirée"
const ROUTES_AUTH = ['/auth/login/', '/auth/register/']

api.interceptors.response.use(
  res => res,
  err => {
    const url = err.config?.url || ''
    const estRouteAuth = ROUTES_AUTH.some(r => url.includes(r))

    if (err.response?.status === 401 && !estRouteAuth) {
      // Session expirée : on prévient AuthContext, qui déconnecte proprement
      // (pas de rechargement de page → plus de page blanche)
      window.dispatchEvent(new CustomEvent('st:session-expiree'))
    }
    if (err.response?.status === 403 && err.response.data?.code === 'changement_mdp_requis') {
      // Mot de passe provisoire : le serveur refuse tout tant qu'il n'est pas changé
      window.dispatchEvent(new CustomEvent('st:mot-de-passe-a-changer'))
    }
    return Promise.reject(err)
  }
)

// Noms des champs affichés dans les messages d'erreur
const LIBELLES_CHAMPS = {
  email: 'Email', password: 'Mot de passe', password2: 'Confirmation du mot de passe',
  nom: 'Nom', prenom: 'Prénom', telephone: 'Téléphone', cni: 'N° CNI', role: 'Rôle', tribunal: 'Tribunal',
  ancien_mdp: 'Mot de passe actuel', nouveau_mdp: 'Nouveau mot de passe', confirmation: 'Confirmation',
}

/** Extrait le message d'erreur le plus lisible d'une réponse Django */
export function messageErreur(err, defaut = 'Une erreur est survenue.') {
  const data = err?.response?.data
  if (!err?.response) return 'Serveur injoignable. Vérifiez votre connexion.'
  if (!data || typeof data !== 'object') return defaut
  if (data.detail) return String(data.detail)
  const champ = Object.keys(data)[0]
  if (!champ) return defaut
  // Tous les messages du champ (ex. mot de passe trop court ET trop courant)
  const val = [].concat(data[champ]).map(String).join(' ')
  if (champ === 'non_field_errors') return val
  return `${LIBELLES_CHAMPS[champ] || champ} : ${val}`
}

/** Les listes DRF peuvent être paginées ({results}) ou non ([]) */
export const liste = (res) => (Array.isArray(res.data) ? res.data : res.data?.results || [])

// ── Auth ──────────────────────────────────
export const authAPI = {
  login:    (data) => api.post('/auth/login/', data),
  register: (data) => api.post('/auth/register/', data),
  logout:   ()     => api.post('/auth/logout/'),
  me:       ()     => api.get('/auth/me/'),
  updateMe: (data) => api.patch('/auth/me/', data),
  changerMotDePasse: (data) => api.post('/auth/changer-mot-de-passe/', data),
}

// ── Personnel judiciaire (greffier en chef) ─
export const staffAPI = {
  list:   ()         => api.get('/auth/staff/'),
  create: (data)     => api.post('/auth/staff/', data),
  update: (id, data) => api.patch(`/auth/staff/${id}/`, data),
  // Nouveau mot de passe provisoire envoyé par e-mail (changement obligatoire à la connexion)
  renvoyer: (id)     => api.post(`/auth/staff/${id}/renvoyer/`),
}

// ── Rendez-vous ───────────────────────────
export const rdvAPI = {
  list:     (params = {}) => api.get('/rdv/', { params }),
  create:   (data) => api.post('/rdv/', data),
  myList:   ()     => api.get('/rdv/my/'),
  update:   (id, data) => api.patch(`/rdv/${id}/`, data),
  valider:  (id)   => api.post(`/rdv/${id}/valider/`),
  rejeter:  (id, motif = '') => api.post(`/rdv/${id}/rejeter/`, { motif }),
  terminer: (id)   => api.post(`/rdv/${id}/terminer/`),
  annuler:  (id)   => api.post(`/rdv/${id}/annuler/`),
  slots:    (tribunalId, date) => api.get(`/rdv/slots/?tribunal=${tribunalId}&date=${date}`),
  services: (tribunalId = '') => api.get(`/rdv/services/?tribunal=${tribunalId}`),
}

// ── Registres du greffe (courrier arrivée / départ + transmission) ─
export const registresAPI = {
  list:        (params = {}) => api.get('/registres/courriers/', { params }),
  detail:      (id)          => api.get(`/registres/courriers/${id}/`),
  create:      (formData)    => api.post('/registres/courriers/', formData,
                                 { headers: { 'Content-Type': 'multipart/form-data' } }),
  transmettre: (id, service_destination, commentaire = '') =>
                 api.post(`/registres/courriers/${id}/transmettre/`, { service_destination, commentaire }),
  accuser:     (id, commentaire = '') => api.post(`/registres/courriers/${id}/accuser_reception/`, { commentaire }),
  traiter:     (id, commentaire = '') => api.post(`/registres/courriers/${id}/traiter/`, { commentaire }),
  expedier:    (id, commentaire = '') => api.post(`/registres/courriers/${id}/expedier/`, { commentaire }),
  archiver:    (id, commentaire = '') => api.post(`/registres/courriers/${id}/archiver/`, { commentaire }),
  stats:       ()            => api.get('/registres/courriers/stats/'),
  services:    ()            => api.get('/registres/courriers/services/'),
  transmissions: (params = {}) => api.get('/registres/transmissions/', { params }),
  exporter:    (params = {}) => api.get('/registres/courriers/export/', { params, responseType: 'blob' }),
}

// ── Archivage numérique des dossiers ──────
export const archivesAPI = {
  list:     (params = {}) => api.get('/archives/dossiers/', { params }),
  detail:   (id)          => api.get(`/archives/dossiers/${id}/`),
  create:   (data)        => api.post('/archives/dossiers/', data),
  update:   (id, data)    => api.patch(`/archives/dossiers/${id}/`, data),
  ajouterPieces: (id, fichiers, type_piece = 'autre') => {
    const fd = new FormData()
    fichiers.forEach(f => fd.append('fichiers', f))
    fd.append('type_piece', type_piece)
    return api.post(`/archives/dossiers/${id}/pieces/`, fd,
      { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
  },
  supprimerPiece: (id, pieceId) => api.delete(`/archives/dossiers/${id}/pieces/${pieceId}/`),
  cloturer: (id, commentaire = '') => api.post(`/archives/dossiers/${id}/cloturer/`, { commentaire }),
  archiver: (id, emplacement)      => api.post(`/archives/dossiers/${id}/archiver/`, emplacement),
  rouvrir:  (id, commentaire = '') => api.post(`/archives/dossiers/${id}/rouvrir/`, { commentaire }),
  stats:    ()                     => api.get('/archives/dossiers/stats/'),
  juges:    ()                     => api.get('/archives/dossiers/juges/'),
}

// ── Journal des SMS (personnel) ───────────
export const smsAPI = {
  list: () => api.get('/notifications/sms/'),
}

// ── Plaintes ──────────────────────────────
export const plainteAPI = {
  list:     (params = {}) => api.get('/plaintes/', { params }),
  create:   (data) => api.post('/plaintes/', data,
                        { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 }),
  myList:   ()     => api.get('/plaintes/my/'),
  detail:   (id)   => api.get(`/plaintes/${id}/`),
  instruire:(id)   => api.post(`/plaintes/${id}/instruire/`),
  urgent:   (id)   => api.post(`/plaintes/${id}/urgent/`),
  traiter:  (id, commentaire = '') => api.post(`/plaintes/${id}/traiter/`, { commentaire }),
  rejeter:  (id, motif) => api.post(`/plaintes/${id}/rejeter/`, { motif }),
  assigner: (id, juge)  => api.post(`/plaintes/${id}/assigner/`, { juge }),
  juges:    ()     => api.get('/plaintes/juges/'),
  message:  (id, msg) => api.post(`/plaintes/${id}/message/`, { message: msg }),
}

// ── Alertes SOS ──────────────────────────
export const sosAPI = {
  list:     ()     => api.get('/alertes/'),
  create:   (data) => api.post('/alertes/', data),
  prendreEnCharge: (id) => api.post(`/alertes/${id}/prendre/`),
  cloturer: (id, commentaire = '') => api.post(`/alertes/${id}/cloturer/`, { commentaire }),
}

// ── Courriers citoyen <-> tribunal (inscrits au registre du greffe) ─
const multipart = { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 }
export const courrierAPI = {
  list:     (params = {}) => api.get('/correspondances/', { params }),
  create:   (formData)    => api.post('/correspondances/', formData, multipart),
  repondre: (id, formData) => api.post(`/correspondances/${id}/repondre/`, formData, multipart),
  lu:       (id)          => api.post(`/correspondances/${id}/lu/`),
  citoyens: (q = '')      => api.get('/correspondances/citoyens/', { params: { q } }),
  dossiers: (citoyen = '') => api.get('/correspondances/dossiers/', { params: citoyen ? { citoyen } : {} }),
}

// ── Tribunaux ─────────────────────────────
export const tribunalAPI = {
  list:   () => api.get('/rdv/tribunaux/'),
  detail: (id) => api.get(`/rdv/tribunaux/${id}/`),
}

// ── Statistiques (chiffres réels) ─────────
export const statsAPI = {
  badges:     () => api.get('/stats/badges/'),
  dashboard:  () => api.get('/stats/dashboard/'),
  analytique: () => api.get('/stats/analytique/'),
  citoyen:    () => api.get('/stats/citoyen/'),
}

// ── Notifications ─────────────────────────
export const notifAPI = {
  list:    () => api.get('/notifications/'),
  markRead:(id) => api.post(`/notifications/${id}/read/`),
  markAll: () => api.post('/notifications/read_all/'),
}

export default api
