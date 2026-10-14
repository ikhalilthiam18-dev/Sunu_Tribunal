import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

export const ROLES = {
  CITOYEN:  'citoyen',
  ADMIN:    'admin',
  JUGE:     'juge',
  GREFFIER: 'greffier',
  ACCUEIL:  'accueil',
  COURRIER: 'courrier',
  AVOCAT:   'avocat',
}

// Libellés affichés dans l'interface
export const ROLE_LABELS = {
  admin:    'Greffier en chef',
  juge:     'Juge',
  greffier: 'Greffier',
  accueil:  'Accueil et orientation',
  courrier: 'Bureau courrier',
  citoyen:  'Citoyen',
  avocat:   'Avocat',
}

// Personnel du tribunal → espace Admin
export const STAFF_ROLES   = [ROLES.ADMIN, ROLES.JUGE, ROLES.GREFFIER, ROLES.ACCUEIL, ROLES.COURRIER]
// Usagers → espace Citoyen
export const CITOYEN_ROLES = [ROLES.CITOYEN, ROLES.AVOCAT]

/** Page où l'utilisateur doit définir son mot de passe (mot de passe temporaire) */
export const PAGE_MOT_DE_PASSE = '/changer-mot-de-passe'

/** Page d'accueil selon le rôle (null = rôle non pris en charge) */
export function homePathFor(role) {
  if (STAFF_ROLES.includes(role))   return '/admin'
  if (CITOYEN_ROLES.includes(role)) return '/citoyen'
  return null
}

/** Vérifie qu'un token JWT existe et n'est pas expiré */
function tokenValide(token) {
  if (!token) return false
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const payload = JSON.parse(atob(base64))
    return !payload.exp || payload.exp * 1000 > Date.now()
  } catch {
    return false
  }
}

/** Relit la session sauvegardée ; la nettoie si elle est invalide */
function lireSession() {
  try {
    const token = localStorage.getItem('st_token')
    const user  = JSON.parse(localStorage.getItem('st_user') || 'null')
    if (user && tokenValide(token) && homePathFor(user.role)) {
      return { user, token }
    }
  } catch { /* session corrompue */ }
  localStorage.removeItem('st_user')
  localStorage.removeItem('st_token')
  return { user: null, token: null }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(lireSession)

  const login = useCallback((userData, authToken) => {
    localStorage.setItem('st_user', JSON.stringify(userData))
    localStorage.setItem('st_token', authToken)
    setSession({ user: userData, token: authToken })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('st_user')
    localStorage.removeItem('st_token')
    setSession({ user: null, token: null })
  }, [])

  /** Met à jour une partie du profil en session (ex. doit_changer_mdp après le changement) */
  const majUtilisateur = useCallback((champs) => {
    setSession(s => {
      if (!s.user) return s
      const user = { ...s.user, ...champs }
      localStorage.setItem('st_user', JSON.stringify(user))
      return { ...s, user }
    })
  }, [])

  // Déconnexion automatique quand l'API répond 401 (voir services/api.js)
  useEffect(() => {
    const onExpire = () => logout()
    window.addEventListener('st:session-expiree', onExpire)
    return () => window.removeEventListener('st:session-expiree', onExpire)
  }, [logout])

  // Le serveur exige le changement du mot de passe temporaire → la page dédiée s'ouvre
  useEffect(() => {
    const onMdp = () => majUtilisateur({ doit_changer_mdp: true })
    window.addEventListener('st:mot-de-passe-a-changer', onMdp)
    return () => window.removeEventListener('st:mot-de-passe-a-changer', onMdp)
  }, [majUtilisateur])

  const { user, token } = session

  return (
    <AuthContext.Provider value={{
      user, token, login, logout, majUtilisateur,
      doitChangerMdp: !!user?.doit_changer_mdp,
      isAuth:  !!user && !!token,
      isStaff: !!user && STAFF_ROLES.includes(user.role),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
