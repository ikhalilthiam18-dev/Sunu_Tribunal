import { useCallback, useEffect, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { FiChevronsLeft, FiChevronsRight, FiLogOut, FiX } from 'react-icons/fi'
import Logo from './Logo.jsx'

/**
 * Menu latéral repliable, partagé par l'espace citoyen et l'espace tribunal.
 *
 *   const menu = useSidebarRepliable('citoyen')   // état mémorisé séparément par espace
 *   <Sidebar {...menu} ... />                      // ordinateur (≥ 1024 px)
 *   <Sidebar {...menu} mobile ... />               // tiroir mobile / APK
 */

const LARGEUR = { ouvert: 'w-64', replie: 'w-[76px]' }

// ── Lecture / écriture du choix, protégées (stockage indisponible en navigation privée, etc.) ──
function lireChoix(cle) {
  try { return localStorage.getItem(cle) === 'replie' } catch { return false }
}
function ecrireChoix(cle, replie) {
  try { localStorage.setItem(cle, replie ? 'replie' : 'ouvert') } catch { /* sans mémorisation */ }
}

export function useSidebarRepliable(espace) {
  const cle = `st_menu_${espace}`
  const [replie, setReplie] = useState(() => lireChoix(cle))
  const [mobileOuvert, setMobileOuvert] = useState(false)

  const basculer = useCallback(() => {
    setReplie(r => { ecrireChoix(cle, !r); return !r })
  }, [cle])
  const ouvrirMobile = useCallback(() => setMobileOuvert(true), [])
  const fermerMobile = useCallback(() => setMobileOuvert(false), [])

  // Échap ferme le tiroir mobile
  useEffect(() => {
    if (!mobileOuvert) return
    const surTouche = (e) => { if (e.key === 'Escape') setMobileOuvert(false) }
    window.addEventListener('keydown', surTouche)
    return () => window.removeEventListener('keydown', surTouche)
  }, [mobileOuvert])

  return { replie, basculer, mobileOuvert, ouvrirMobile, fermerMobile }
}

// ── Infobulle du mode replié ──
// Affichée en position fixe : elle n'est pas coupée par le menu (overflow-hidden pendant l'animation).
function useInfobulle(actif) {
  const [bulle, setBulle] = useState(null)
  const montrer = (texte) => (e) => {
    if (!actif) return
    const r = e.currentTarget.getBoundingClientRect()
    setBulle({ texte, top: r.top + r.height / 2, left: r.right + 10 })
  }
  const cacher = () => setBulle(null)
  useEffect(() => { if (!actif) setBulle(null) }, [actif])
  const props = (texte) => ({
    onMouseEnter: montrer(texte), onMouseLeave: cacher, onFocus: montrer(texte), onBlur: cacher,
  })
  const rendu = bulle && (
    <span role="tooltip"
      className="fixed z-[60] -translate-y-1/2 pointer-events-none whitespace-nowrap rounded-lg bg-navy-900 text-white text-xs font-medium px-2.5 py-1.5 shadow-lg animate-fade-in"
      style={{ top: bulle.top, left: bulle.left }}>
      {bulle.texte}
    </span>
  )
  return { props, rendu }
}

const nombre = (n, max = 99) => (n > max ? `${max}+` : n)

/**
 * liens       : [{ to, label, icon, exact, compteur, urgent }]  (déjà filtrés selon le rôle)
 * sos         : lien d'urgence toujours visible (espace citoyen), ou null
 * enTete      : texte sous le logo (ex. « Administration · TGI Dakar »), caché en mode replié
 * utilisateur : { initiale, nom, detail, avatarClasse, icone }
 */
export function Sidebar({
  couleur, liens, sos = null, enTete = null, utilisateur, onDeconnexion,
  replie, basculer, mobile = false, fermerMobile,
}) {
  const compact = replie && !mobile            // le mode icônes n'existe que sur ordinateur
  const bulle = useInfobulle(compact)
  const apresNavigation = mobile ? fermerMobile : undefined

  const clicLogo = mobile ? fermerMobile : basculer
  const libelleLogo = mobile ? 'Fermer le menu' : (replie ? 'Agrandir le menu' : 'Réduire le menu')

  const classeLien = (isActive, extra = '') =>
    `sidebar-item relative ${isActive ? 'active' : ''} ${compact ? 'justify-center !px-0' : ''} ${extra}`

  return (
    <aside
      className={mobile
        ? `absolute left-0 top-0 bottom-0 w-72 ${couleur} text-white flex flex-col z-50 animate-slide-in`
        : `hidden lg:flex flex-col ${couleur} text-white flex-shrink-0 overflow-hidden
           transition-[width] duration-200 ease-out ${compact ? LARGEUR.replie : LARGEUR.ouvert}`}
      aria-label="Menu principal">

      {/* ── Logo : bouton replier / déplier (ou fermer sur mobile) ── */}
      <div className={`border-b border-white/10 ${compact ? 'px-2 py-4' : 'p-5'}`}>
        <div className="flex items-center gap-2">
          <button type="button" onClick={clicLogo}
            aria-label={libelleLogo} aria-expanded={mobile ? true : !replie} title={libelleLogo}
            className={`group flex items-center gap-1.5 rounded-xl min-w-0 transition-colors hover:bg-white/5
                        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold-400
                        ${compact ? 'w-full justify-center p-1' : 'p-1 -m-1'}`}>
            {compact
              ? <Logo compact size="xs" />
              : <Logo fond="sombre" size={mobile ? 'sm' : 'md'} />}
            {!mobile && (compact
              ? <FiChevronsRight className="w-3.5 h-3.5 text-white/50 group-hover:text-white flex-shrink-0" aria-hidden="true" />
              : <FiChevronsLeft className="w-4 h-4 text-white/50 group-hover:text-white flex-shrink-0" aria-hidden="true" />)}
          </button>
          {mobile && (
            <button type="button" onClick={fermerMobile} aria-label="Fermer le menu"
              className="ml-auto p-1 rounded-lg text-white/70 hover:text-white">
              <FiX className="w-6 h-6" />
            </button>
          )}
        </div>
        {enTete && !compact && (
          <p className="text-xs text-white/55 mt-2 uppercase tracking-widest truncate">{enTete}</p>
        )}
      </div>

      {/* ── Liens ── */}
      <nav className={`flex-1 overflow-y-auto overflow-x-hidden ${compact ? 'px-2 py-3' : 'p-3'}`}>
        {!compact && (
          <p className="text-xs text-white/60 uppercase tracking-widest px-2 mb-3 font-semibold">Navigation</p>
        )}
        {liens.map(lien => (
          <NavLink key={lien.to} to={lien.to} end={lien.exact} onClick={apresNavigation}
            aria-label={compact ? lien.label : undefined} {...bulle.props(lien.label)}
            className={({ isActive }) => classeLien(isActive, lien.urgent ? 'mt-1' : '')}>
            <span className="relative flex-shrink-0">
              <lien.icon className={compact ? 'w-5 h-5' : 'w-4 h-4'} />
              {/* Mode replié : compteur en pastille sur l'icône */}
              {compact && lien.compteur > 0 && (
                <span className={`absolute -top-2 -right-2.5 min-w-4 h-4 px-1 rounded-full text-[10px] font-bold leading-4 text-center ${
                  lien.urgent ? 'bg-red-500 text-white' : 'bg-gold-400 text-navy-700'}`}>
                  {nombre(lien.compteur, 9)}
                </span>
              )}
            </span>
            {!compact && <span className="flex-1 truncate">{lien.label}</span>}
            {!compact && lien.compteur > 0 && (
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full min-w-5 text-center ${
                lien.urgent ? 'bg-red-500 text-white' : 'bg-white/20 text-white'}`}>
                {nombre(lien.compteur)}
              </span>
            )}
          </NavLink>
        ))}

        {/* Alerte SOS : toujours visible, même en mode replié */}
        {sos && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <NavLink to={sos.to} onClick={apresNavigation}
              aria-label={compact ? sos.label : undefined} {...bulle.props(sos.label)}
              className={() => classeLien(false, 'bg-red-600/20 hover:bg-red-600/30 text-red-200 border border-red-500/30')}>
              <sos.icon className={`flex-shrink-0 ${compact ? 'w-5 h-5' : 'w-4 h-4'}`} />
              {!compact && <span className="truncate">{sos.label}</span>}
            </NavLink>
          </div>
        )}
      </nav>

      {/* ── Utilisateur et déconnexion ── */}
      <div className={`border-t border-white/10 ${compact ? 'px-2 py-3 flex flex-col items-center gap-2' : 'p-4'}`}>
        {compact ? (
          <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold ${utilisateur.avatarClasse}`}
            {...bulle.props(utilisateur.nom || 'Mon compte')} tabIndex={0} aria-label={utilisateur.nom}>
            {utilisateur.initiale}
          </div>
        ) : (
          <div className={`flex items-center gap-3 mb-3 ${utilisateur.encadre ? 'bg-white/5 rounded-xl p-3' : ''}`}>
            <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0 ${utilisateur.avatarClasse}`}>
              {utilisateur.initiale}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-white truncate">{utilisateur.nom}</p>
              <p className="text-xs text-white/60 truncate">{utilisateur.detail}</p>
            </div>
            {utilisateur.icone}
          </div>
        )}
        <button type="button" onClick={onDeconnexion}
          aria-label={compact ? 'Déconnexion' : undefined} {...bulle.props('Déconnexion')}
          className={`sidebar-item text-white/60 hover:text-white ${compact ? 'justify-center !px-0 w-11' : 'w-full'}`}>
          <FiLogOut className={compact ? 'w-5 h-5' : 'w-4 h-4'} />
          {!compact && 'Deconnexion'}
        </button>
      </div>

      {bulle.rendu}
    </aside>
  )
}

/** Tiroir mobile (écrans < 1024 px et APK) : fond assombri + menu par-dessus la page */
export function TiroirMobile({ ouvert, fermer, children }) {
  if (!ouvert) return null
  return (
    <div className="lg:hidden fixed inset-0 z-40">
      <div className="absolute inset-0 bg-black/50" onClick={fermer} aria-hidden="true" />
      {children}
    </div>
  )
}
