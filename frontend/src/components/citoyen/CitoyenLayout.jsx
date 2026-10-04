import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  FiHome, FiCalendar, FiFileText, FiMapPin, FiBell,
  FiAlertTriangle, FiMenu, FiMail
} from 'react-icons/fi'
import { useAuth } from '../../context/AuthContext.jsx'
import { useCompteurs } from '../../context/CompteursContext.jsx'
import Logo from '../common/Logo.jsx'
import { Sidebar, TiroirMobile, useSidebarRepliable } from '../common/SidebarRepliable.jsx'
import AssistantJuridique from '../common/AssistantJuridique.jsx'
import toast from 'react-hot-toast'

const navItems = [
  { to: '/citoyen',          icon: FiHome,      label: 'Accueil',      exact: true },
  { to: '/citoyen/rdv',      icon: FiCalendar,  label: 'RDV'               },
  { to: '/citoyen/plainte',  icon: FiFileText,  label: 'Plainte'           },
  { to: '/citoyen/suivi',    icon: FiFileText,  label: 'Mes dossiers'      },
  { to: '/citoyen/courrier', icon: FiMail,      label: 'Courriers',     badge: 'courriers' },
  { to: '/citoyen/carte',    icon: FiMapPin,    label: 'Carte'             },
  { to: '/citoyen/notifs',   icon: FiBell,      label: 'Notifications', badge: 'notifs' },
]

const bottomNav = [
  { to: '/citoyen',         icon: FiHome,     label: 'Accueil', exact: true },
  { to: '/citoyen/rdv',     icon: FiCalendar, label: 'RDV'                 },
  { to: '/citoyen/plainte', icon: FiFileText, label: 'Plainte'             },
  { to: '/citoyen/suivi',   icon: FiFileText, label: 'Mes dossiers'        },
]

export default function CitoyenLayout() {
  const { user, logout } = useAuth()
  const { compteurs } = useCompteurs()
  const navigate = useNavigate()
  const menu = useSidebarRepliable('citoyen')

  const handleLogout = () => {
    logout()
    navigate('/')
    toast.success('Deconnecte avec succes')
  }

  const proprietesMenu = {
    couleur: 'bg-justice-600',
    liens: navItems.map(item => ({ ...item, compteur: item.badge ? compteurs[item.badge] : 0 })),
    // Alerte SOS : jamais masquée, même menu replié
    sos: { to: '/citoyen/sos', label: 'Alerte SOS', icon: FiAlertTriangle },
    utilisateur: {
      initiale: user?.nom?.[0] || 'C',
      nom: user?.nom,
      detail: user?.email,
      avatarClasse: 'bg-white/20 text-white',
    },
    onDeconnexion: handleLogout,
    ...menu,
  }

  return (
    <div className="flex h-screen bg-gray-50">

      {/* Ordinateur : menu repliable (clic sur le logo) */}
      <Sidebar {...proprietesMenu} />

      {/* Mobile / APK : menu par-dessus la page */}
      <TiroirMobile ouvert={menu.mobileOuvert} fermer={menu.fermerMobile}>
        <Sidebar {...proprietesMenu} mobile />
      </TiroirMobile>

      {/* ── Main content : s'élargit automatiquement quand le menu se replie ── */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">

        {/* Mobile topbar */}
        <header className="lg:hidden bg-justice-600 text-white px-4 py-3 flex items-center justify-between">
          <button onClick={menu.ouvrirMobile} aria-label="Ouvrir le menu" aria-expanded={menu.mobileOuvert}>
            <FiMenu className="w-6 h-6" />
          </button>
          <Logo fond="sombre" size="sm" />
          <NavLink to="/citoyen/notifs" className="relative">
            <FiBell className="w-6 h-6" />
            {compteurs.notifs > 0 && (
              <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs min-w-4 h-4 px-0.5 rounded-full flex items-center justify-center font-bold">
                {compteurs.notifs > 9 ? '9+' : compteurs.notifs}
              </span>
            )}
          </NavLink>
        </header>

        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>

        {/* Mobile bottom nav */}
        <nav className="lg:hidden bg-white border-t border-gray-100 flex">
          {bottomNav.map(item => (
            <NavLink key={item.to} to={item.to} end={item.exact}
              className={({ isActive }) =>
                `flex-1 flex flex-col items-center py-2 gap-0.5 text-xs transition-colors ${
                  isActive ? 'text-justice-500' : 'text-gray-400'
                }`}>
              <item.icon className="w-5 h-5" />
              {item.label.split(' ')[0]}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Assistant Juridique flottant */}
      <AssistantJuridique />
    </div>
  )
}