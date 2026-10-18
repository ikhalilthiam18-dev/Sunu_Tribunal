import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  FiGrid, FiCalendar, FiFileText, FiAlertTriangle,
  FiBarChart2, FiMenu,
  FiBell, FiMail, FiShield, FiUsers, FiBookOpen, FiArchive
} from 'react-icons/fi'
import { useAuth, ROLE_LABELS } from '../../context/AuthContext.jsx'
import { useCompteurs } from '../../context/CompteursContext.jsx'
import { Sidebar, TiroirMobile, useSidebarRepliable } from '../common/SidebarRepliable.jsx'
import AssistantAdmin from '../admin/AssistantAdmin.jsx'
import Logo from '../common/Logo.jsx'
import toast from 'react-hot-toast'

// roles : qui voit le lien (absent = tout le personnel)
// Organisation reelle du greffe : l'accueil gere les RDV, le bureau courrier gere les registres
const navItems = [
  { to:'/admin',           icon:FiGrid,          label:'Vue generale',  exact:true, badge:null        },
  { to:'/admin/rdv',       icon:FiCalendar,      label:'Rendez-vous',   badge:'rdv',
    roles:['admin','juge','greffier','accueil'] },
  { to:'/admin/plaintes',  icon:FiFileText,      label:'Plaintes',      badge:'plaintes',
    roles:['admin','juge','greffier'] },
  { to:'/admin/registres', icon:FiBookOpen,      label:'Registres',     badge:null,
    roles:['admin','greffier','courrier'] },
  { to:'/admin/courrier',  icon:FiMail,          label:'Courriers',     badge:'courriers',
    roles:['admin','greffier','courrier','accueil'] },
  { to:'/admin/alertes',   icon:FiAlertTriangle, label:'Alertes SOS',   badge:'alertes',  urgent:true,
    roles:['admin','juge','greffier','accueil'] },
  { to:'/admin/stats',     icon:FiBarChart2,     label:'Statistiques',  badge:null,
    roles:['admin','juge','greffier'] },
  { to:'/admin/dossiers',  icon:FiArchive,       label:'Archives',      badge:null,
    roles:['admin','juge','greffier','courrier'] },
  { to:'/admin/utilisateurs', icon:FiUsers, label:'Personnel', badge:null, roles:['admin'] },
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const { compteurs } = useCompteurs()
  const navigate = useNavigate()
  const menu = useSidebarRepliable('tribunal')
  const tribunal = user?.tribunal_nom || 'Tous les tribunaux'

  const handleLogout = () => {
    logout()
    navigate('/')
    toast.success('Deconnecte avec succes')
  }

  // Liens filtrés selon le rôle de l'agent, avec leurs compteurs
  const liens = navItems
    .filter(item => !item.roles || item.roles.includes(user?.role))
    .map(item => ({ ...item, compteur: item.badge ? compteurs[item.badge] : 0 }))

  const proprietesMenu = {
    couleur: 'bg-navy-700',
    liens,
    enTete: `Administration · ${tribunal}`,
    utilisateur: {
      initiale: user?.nom?.[0] || 'A',
      nom: user?.nom,
      detail: ROLE_LABELS[user?.role] || 'Personnel',
      avatarClasse: 'bg-gold-400/30 text-gold-400',
      encadre: true,
      icone: <FiShield className="w-4 h-4 text-gold-400 flex-shrink-0" />,
    },
    onDeconnexion: handleLogout,
    ...menu,
  }

  return (
    <div className="flex hauteur-ecran bg-gray-50">

      {/* Ordinateur : menu repliable (clic sur le logo) */}
      <Sidebar {...proprietesMenu} />

      {/* Mobile / APK : menu par-dessus la page */}
      <TiroirMobile ouvert={menu.mobileOuvert} fermer={menu.fermerMobile}>
        <Sidebar {...proprietesMenu} mobile />
      </TiroirMobile>

      {/* Main : s'élargit automatiquement quand le menu se replie */}
      <div className="flex-1 min-w-0 flex flex-col overflow-hidden">

        {/* Topbar */}
        <header className="bg-white border-b border-gray-100 px-4 lg:px-6 py-3 flex items-center justify-between">
          <button className="lg:hidden" onClick={menu.ouvrirMobile}
            aria-label="Ouvrir le menu" aria-expanded={menu.mobileOuvert}>
            <FiMenu className="w-6 h-6 text-gray-600" />
          </button>
          <Logo fond="clair" size="sm" className="lg:hidden ml-3 min-w-0" />
          <div className="hidden lg:block">
            <p className="text-xs text-gray-400 uppercase tracking-wide">
              Tribunal de Grande Instance
            </p>
            <p className="font-semibold text-navy-700 text-sm">{tribunal}</p>
          </div>
          <div className="flex items-center gap-3 ml-auto">
            <NavLink to="/admin/notifs" title="Notifications"
              className="relative p-2 hover:bg-gray-100 rounded-xl transition-colors">
              <FiBell className="w-5 h-5 text-gray-600" />
              {compteurs.notifs > 0 && (
                <span className="absolute top-1 right-1 min-w-4 h-4 px-0.5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center font-bold">
                  {compteurs.notifs > 9 ? '9+' : compteurs.notifs}
                </span>
              )}
            </NavLink>
            <div className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-1.5 border border-gray-200">
              <div className="w-7 h-7 rounded-full bg-navy-700 flex items-center justify-center text-white text-xs font-bold">
                {user?.nom?.[0] || 'A'}
              </div>
              <span className="text-sm font-medium text-navy-700 hidden sm:block">
                {user?.nom}
              </span>
            </div>
          </div>
        </header>

        {/* pb mobile : la fin de la page reste visible au-dessus du bouton de l'assistant */}
        <main className="flex-1 overflow-y-auto pb-24 lg:pb-0">
          <Outlet />
        </main>
      </div>

      {/* Assistant Admin flottant */}
      <AssistantAdmin />
    </div>
  )
}