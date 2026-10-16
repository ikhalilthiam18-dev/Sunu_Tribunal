import { useEffect, useRef, useState } from 'react'
import { FiNavigation, FiPhone, FiClock } from 'react-icons/fi'
import toast from 'react-hot-toast'
import { tribunalAPI, liste, messageErreur } from '../../services/api.js'

// Distance à vol d'oiseau (km) entre la position du citoyen et un tribunal
function distanceKm(a, b) {
  const R = 6371, rad = (x) => x * Math.PI / 180
  const dLat = rad(b.lat - a.lat), dLng = rad(b.lng - a.lng)
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2
  return 2 * R * Math.asin(Math.sqrt(h))
}
const fmtDistance = (km) => km < 10 ? `${km.toFixed(1)} km` : `${Math.round(km)} km`

// Recherche tolérante : « Thiès » trouve « Thies », sans tenir compte des majuscules
const sansAccents = (s) => (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()

// Tribunaux de la base (Django Admin) → format de la carte
const versCarte = (t) => ({
  id: t.id, nom: t.nom, adresse: t.adresse, tel: t.telephone, heures: t.heures_ouverture,
  lat: t.latitude !== null ? Number(t.latitude) : null,
  lng: t.longitude !== null ? Number(t.longitude) : null,
})

export default function CartePage() {
  const mapRef     = useRef(null)
  const mapInst    = useRef(null)
  const [selected, setSelected] = useState(null)
  const [search,   setSearch]   = useState('')
  const [tribunaux, setTribunaux] = useState([])
  const [position, setPosition] = useState(null)
  const [cartePrete, setCartePrete] = useState(false)

  useEffect(() => {
    tribunalAPI.list()
      .then(r => setTribunaux(liste(r).map(versCarte)))
      .catch(err => toast.error(messageErreur(err, 'Impossible de charger les tribunaux.')))
    navigator.geolocation?.getCurrentPosition(
      p => setPosition({ lat: p.coords.latitude, lng: p.coords.longitude }), () => {})
  }, [])

  useEffect(() => {
    if (mapInst.current) return
    import('leaflet').then(L => {
      mapInst.current = L.map(mapRef.current, {
        center: [14.6928, -17.4467], zoom: 12
      })
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
      }).addTo(mapInst.current)
      setCartePrete(true)
    })
    return () => { if (mapInst.current) { mapInst.current.remove(); mapInst.current = null } }
  }, [])

  // Marqueurs : ajoutés quand la carte et la liste des tribunaux sont prêtes
  useEffect(() => {
    if (!cartePrete || !mapInst.current) return
    import('leaflet').then(L => {
      tribunaux.filter(t => t.lat !== null && t.lng !== null).forEach(t => {
        const icon = L.divIcon({
          className: '',
          html: `<div style="background:#0E1A2B;color:#C9A45C;width:28px;height:28px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);border:2px solid #C9A45C;box-shadow:0 4px 10px rgba(14,26,43,0.25);display:flex;align-items:center;justify-content:center;"><span style="transform:rotate(45deg);font-size:11px;font-weight:800;">⚖</span></div>`,
          iconSize: [28, 28],
          iconAnchor: [14, 28],
        })
        L.marker([t.lat, t.lng], { icon })
          .addTo(mapInst.current)
          .bindPopup(`<strong>${t.nom}</strong><br/>${t.adresse}`)
      })
    })
  }, [cartePrete, tribunaux])

  // Chaque mot tapé doit figurer dans le nom ou l'adresse, dans n'importe quel ordre
  const mots = sansAccents(search).split(/\s+/).filter(Boolean)
  const filtered = tribunaux
    .map(t => ({ ...t, km: position && t.lat !== null ? distanceKm(position, t) : null }))
    .filter(t => {
      const texte = sansAccents(`${t.nom} ${t.adresse}`)
      return mots.every(m => texte.includes(m))
    })
    .sort((a, b) => (a.km ?? Infinity) - (b.km ?? Infinity))

  const flyTo = (t) => {
    setSelected(t.id)
    if (t.lat !== null) mapInst.current?.flyTo([t.lat, t.lng], 15, { duration: 1 })
  }

  return (
    <div className="p-4 lg:p-6 max-w-4xl mx-auto">
      <div className="mb-4">
        <h1 className="font-display text-2xl font-bold text-navy-700">Localisation des tribunaux</h1>
        <p className="text-gray-500 text-sm mt-1">Trouvez le tribunal le plus proche</p>
      </div>

      {/* Map */}
      <div className="rounded-2xl overflow-hidden border border-gray-200 mb-4 shadow-card" style={{ height: 280 }}>
        <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
      </div>

      {/* Search */}
      <input className="form-input mb-4" placeholder="🔍 Rechercher un tribunal..."
        value={search} onChange={e => setSearch(e.target.value)} />

      {/* List */}
      <div className="space-y-3">
        {filtered.length === 0 && (
          <div className="card text-center text-sm text-gray-500 py-8">
            {tribunaux.length === 0
              ? 'Aucun tribunal enregistré pour le moment.'
              : `Aucun tribunal ne correspond à « ${search.trim()} ».`}
          </div>
        )}
        {filtered.map(t => (
          <div key={t.id}
            onClick={() => flyTo(t)}
            className={`card cursor-pointer transition-all ${
              selected === t.id ? 'border-navy-700 ring-1 ring-navy-700' : 'hover:shadow-card-hover'
            }`}>
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-justice-400" />
                  <h3 className="font-semibold text-navy-700 text-sm">{t.nom}</h3>
                </div>
                <p className="text-xs text-gray-500 mt-1 ml-4">{t.adresse}</p>
              </div>
              {t.km !== null && (
                <span className="text-xs font-semibold text-justice-500 bg-justice-50 px-2 py-1 rounded-full ml-2 flex-shrink-0">
                  {fmtDistance(t.km)}
                </span>
              )}
            </div>
            <div className="flex items-center gap-4 ml-4 text-xs text-gray-500">
              {t.tel && <span className="flex items-center gap-1"><FiPhone className="w-3 h-3" />{t.tel}</span>}
              <span className="flex items-center gap-1"><FiClock className="w-3 h-3" />{t.heures}</span>
            </div>
            <div className="flex gap-2 mt-3 ml-4">
              <a href={`https://maps.google.com/?q=${t.lat},${t.lng}`} target="_blank" rel="noreferrer"
                className="flex items-center gap-1.5 text-xs font-semibold text-navy-700 bg-navy-50 px-3 py-1.5 rounded-lg hover:bg-navy-100 transition-colors"
                onClick={e => e.stopPropagation()}>
                <FiNavigation className="w-3 h-3" /> Itinéraire
              </a>
              {t.tel && <a href={`tel:${t.tel}`}
                className="flex items-center gap-1.5 text-xs font-semibold text-justice-600 bg-justice-50 px-3 py-1.5 rounded-lg hover:bg-justice-100 transition-colors"
                onClick={e => e.stopPropagation()}>
                <FiPhone className="w-3 h-3" /> Appeler
              </a>}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
