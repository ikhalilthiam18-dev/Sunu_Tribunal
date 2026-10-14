import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth, homePathFor, STAFF_ROLES, CITOYEN_ROLES, PAGE_MOT_DE_PASSE } from './context/AuthContext.jsx'
import { CompteursProvider } from './context/CompteursContext.jsx'
import ErrorBoundary from './components/common/ErrorBoundary.jsx'

// Pages publiques
import LandingPage from './pages/LandingPage.jsx'
import MotDePassePage from './pages/MotDePassePage.jsx'

// Citoyen
import CitoyenLayout  from './components/citoyen/CitoyenLayout.jsx'
import CitoyenHome    from './pages/citoyen/CitoyenHome.jsx'
import RDVPage        from './pages/citoyen/RDVPage.jsx'
import PlaintePage    from './pages/citoyen/PlaintePage.jsx'
import SuiviPage      from './pages/citoyen/SuiviPage.jsx'
import CartePage      from './pages/citoyen/CartePage.jsx'
import NotifsPage     from './pages/citoyen/NotifsPage.jsx'
import SOSPage        from './pages/citoyen/SOSPage.jsx'
import CourrierPage   from './pages/citoyen/CourrierPage.jsx'

// Admin
import AdminLayout       from './components/admin/AdminLayout.jsx'
import AdminHome         from './pages/admin/AdminHome.jsx'
import AdminRDV          from './pages/admin/AdminRDV.jsx'
import AdminPlaintes     from './pages/admin/AdminPlaintes.jsx'
import AdminAlertes      from './pages/admin/AdminAlertes.jsx'
import AdminStats        from './pages/admin/AdminStats.jsx'
import AdminDossiers     from './pages/admin/AdminDossiers.jsx'
import AdminCourrier     from './pages/admin/AdminCourrier.jsx'
import AdminUtilisateurs from './pages/admin/AdminUtilisateurs.jsx'
import AdminRegistres    from './pages/admin/AdminRegistres.jsx'

function ProtectedRoute({ children, roles }) {
  const { isAuth, user } = useAuth()
  if (!isAuth) return <Navigate to="/" replace />
  // Mot de passe temporaire : tout l'espace reste bloqué tant qu'il n'est pas changé
  if (user.doit_changer_mdp) return <Navigate to={PAGE_MOT_DE_PASSE} replace />
  if (!roles.includes(user.role)) {
    // Mauvais espace : on envoie directement vers le BON espace
    // (jamais vers "/" → c'est ce qui créait la boucle infinie / page blanche)
    const home = homePathFor(user.role)
    return <Navigate to={home || '/'} replace />
  }
  return children
}

function AppRoutes() {
  const { isAuth, user } = useAuth()
  const home = isAuth ? (user.doit_changer_mdp ? PAGE_MOT_DE_PASSE : homePathFor(user.role)) : null

  return (
    <Routes>
      {/* Page d'accueil : redirection unique selon le rôle */}
      <Route path="/" element={home ? <Navigate to={home} replace /> : <LandingPage />} />

      {/* Changer son mot de passe : obligatoire si provisoire (1re connexion), sinon depuis le menu */}
      <Route path={PAGE_MOT_DE_PASSE} element={
        isAuth ? <MotDePassePage obligatoire={!!user.doit_changer_mdp} /> : <Navigate to="/" replace />
      } />
      <Route path="/mot-de-passe" element={<Navigate to={PAGE_MOT_DE_PASSE} replace />} />

      {/* Ancien login redirige vers accueil */}
      <Route path="/login" element={<Navigate to="/" replace />} />

      {/* Citoyen */}
      <Route path="/citoyen" element={
        <ProtectedRoute roles={CITOYEN_ROLES}>
          <CitoyenLayout />
        </ProtectedRoute>
      }>
        <Route index          element={<CitoyenHome />}  />
        <Route path="rdv"     element={<RDVPage />}      />
        <Route path="plainte" element={<PlaintePage />}  />
        <Route path="suivi"   element={<SuiviPage />}    />
        <Route path="carte"   element={<CartePage />}    />
        <Route path="notifs"  element={<NotifsPage />}   />
        <Route path="sos"     element={<SOSPage />}      />
        <Route path="courrier" element={<CourrierPage />} />
      </Route>

      {/* Admin */}
      <Route path="/admin" element={
        <ProtectedRoute roles={STAFF_ROLES}>
          <AdminLayout />
        </ProtectedRoute>
      }>
        <Route index              element={<AdminHome />}         />
        <Route path="rdv"         element={<AdminRDV />}          />
        <Route path="plaintes"    element={<AdminPlaintes />}     />
        <Route path="alertes"     element={<AdminAlertes />}      />
        <Route path="stats"       element={<AdminStats />}        />
        <Route path="dossiers"    element={<AdminDossiers />}     />
        <Route path="courrier"    element={<AdminCourrier />}     />
        <Route path="utilisateurs" element={<AdminUtilisateurs />} />
        <Route path="registres"   element={<AdminRegistres />}    />
        <Route path="notifs"      element={<NotifsPage />}        />
      </Route>

      {/* Catch all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
    <CompteursProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              borderRadius: '14px',
              fontFamily: 'Manrope, system-ui, sans-serif',
              fontSize: '14px',
              boxShadow: '0 8px 28px rgba(14,26,43,0.12)',
              border: '1px solid #E7E1D4',
              color: '#0E1A2B',
            },
            success: { iconTheme: { primary: '#1F5E4B', secondary: '#fff' } },
            error:   { iconTheme: { primary: '#A23446', secondary: '#fff' } },
          }}
        />
      </BrowserRouter>
    </CompteursProvider>
    </AuthProvider>
    </ErrorBoundary>
  )
}