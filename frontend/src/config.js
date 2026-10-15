/**
 * SunuTribunal — Configuration centrale de l'URL du backend
 * ----------------------------------------------------------
 * UN SEUL endroit à modifier quand le lien ngrok change
 * ou lors du passage à Railway : la variable VITE_API_URL
 * dans frontend/.env (puis relancer npm run dev / npm run build).
 */
import { Capacitor } from '@capacitor/core'

// URL publique du backend (ngrok aujourd'hui, Railway demain)
const URL_PUBLIQUE =
  import.meta.env.VITE_API_URL || 'https://untainted-giving-moustache.ngrok-free.dev/api'

function resoudreApiBase() {
  // 1. Application Android (APK Capacitor) : l'app tourne sur https://localhost,
  //    il faut donc TOUJOURS utiliser l'URL publique.
  if (Capacitor.isNativePlatform()) return URL_PUBLIQUE

  const host = window.location.hostname

  // 2. Navigateur sur le PC de développement
  if (host === 'localhost' || host === '127.0.0.1') return 'http://localhost:8000/api'

  // 3. Téléphone sur le même Wi-Fi (npm run dev -- --host → http://10.x.x.x:3000)
  if (/^\d{1,3}(\.\d{1,3}){3}$/.test(host)) return `http://${host}:8000/api`

  // 4. Frontend ouvert via ngrok (port 3000) ou déployé
  return URL_PUBLIQUE
}

export const API_BASE = resoudreApiBase().replace(/\/+$/, '')

// En-têtes communs : évite la page d'avertissement HTML de ngrok gratuit
export const HEADERS_COMMUNS = {
  'ngrok-skip-browser-warning': 'true',
}

if (import.meta.env.DEV) {
  console.info('[SunuTribunal] API :', API_BASE)
}
