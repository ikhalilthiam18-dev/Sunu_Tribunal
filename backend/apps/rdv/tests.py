"""python manage.py test apps.rdv"""
import datetime
from types import SimpleNamespace
from unittest import mock
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.notifications.models import SMSLog, Notification
from apps.notifications.sms import normaliser_telephone
from apps.rdv.models import Tribunal, RendezVous, BureauService

TWILIO_OK = dict(TWILIO_ACCOUNT_SID='ACtest', TWILIO_AUTH_TOKEN='tok', TWILIO_FROM_NUMBER='+15005550006',
                 BREVO_SMS_SENDER='', SMSGATE_LOGIN='')


class FauxClientTwilio:
    """Remplace twilio.rest.Client : aucun appel réseau, refuse +221770000000 (numéro non vérifié)."""

    def __init__(self, *args, **kwargs):
        self.messages = self

    def create(self, body, from_, to):
        if to == '+221770000000':
            raise Exception('Numero non verifie sur le compte Twilio d\'essai')
        return SimpleNamespace(sid='SMFAKE123')


twilio_simule = mock.patch('twilio.rest.Client', FauxClientTwilio)


def prochain_jour_ouvre():
    d = timezone.localdate() + datetime.timedelta(days=1)
    while d.weekday() >= 5:
        d += datetime.timedelta(days=1)
    return d


class RendezVousTests(APITestCase):

    def setUp(self):
        self.tribunal = Tribunal.objects.create(nom='TGI Dakar', adresse='Dakar')
        self.citoyen = User.objects.create_user('c@test.sn', 'motdepasse123', nom='Diallo',
                                                prenom='Awa', telephone='77 123 45 67')
        self.accueil = User.objects.create_user('a@test.sn', 'motdepasse123', nom='Sy', role='accueil')
        self.jour = prochain_jour_ouvre()

    def _demande(self, heure='09:00', service='depot_dossier'):
        self.client.force_authenticate(self.citoyen)
        return self.client.post('/api/rdv/', {'tribunal': self.tribunal.id, 'service': service,
                                              'date': self.jour.isoformat(), 'heure': heure}, format='json')

    def test_normalisation_telephone(self):
        self.assertEqual(normaliser_telephone('77 123 45 67'), '+221771234567')
        self.assertEqual(normaliser_telephone('00221 77-123-45-67'), '+221771234567')
        self.assertEqual(normaliser_telephone('221771234567'), '+221771234567')
        self.assertEqual(normaliser_telephone('+33612345678'), '+33612345678')
        self.assertIsNone(normaliser_telephone('12'))
        self.assertIsNone(normaliser_telephone(''))

    def test_demande_puis_creneau_occupe(self):
        r = self._demande()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertIsNone(r.data['orientation'])  # pas de ticket avant confirmation
        self.assertIn("Carte nationale d'identité (CNI)", r.data['pieces_a_fournir'])
        r2 = self._demande()
        self.assertEqual(r2.status_code, 400)
        self.assertIn('heure', r2.data)
        slots = {s['heure']: s['disponible'] for s in self.client.get(
            f'/api/rdv/slots/?tribunal={self.tribunal.id}&date={self.jour.isoformat()}').data}
        self.assertFalse(slots['09:00'])
        self.assertTrue(slots['10:00'])

    def test_regles_date_et_heure(self):
        self.client.force_authenticate(self.citoyen)
        samedi = self.jour + datetime.timedelta(days=(5 - self.jour.weekday()) % 7)
        for data, champ in [({'date': '2020-01-06', 'heure': '09:00'}, 'date'),
                            ({'date': samedi.isoformat(), 'heure': '09:00'}, 'date'),
                            ({'date': self.jour.isoformat(), 'heure': '12:30'}, 'heure')]:
            r = self.client.post('/api/rdv/', {'tribunal': self.tribunal.id, 'service': 'civil', **data}, format='json')
            self.assertEqual(r.status_code, 400)
            self.assertIn(champ, r.data)

    @override_settings(**TWILIO_OK)
    @twilio_simule
    def test_validation_envoie_un_vrai_sms_et_donne_le_ticket(self):
        BureauService.objects.create(tribunal=self.tribunal, service='depot_dossier',
                                     bureau='Bureau 4 — Greffe', localisation='1er étage')
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        r = self.client.post(f'/api/rdv/{rid}/valider/')
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data['sms'], 'envoye')
        log = SMSLog.objects.get()
        self.assertEqual((log.telephone, log.sid), ('+221771234567', 'SMFAKE123'))
        self.assertIn('CONFIRME', log.message)
        self.assertIn('Bureau 4', log.message)
        self.assertNotIn('é', log.message)  # SMS sans accents
        self.assertEqual(r.data['rdv']['orientation']['bureau'], 'Bureau 4 — Greffe')
        self.assertTrue(Notification.objects.filter(destinataire=self.citoyen, titre='Rendez-vous confirmé').exists())
        # déjà traité
        self.assertEqual(self.client.post(f'/api/rdv/{rid}/valider/').status_code, 400)

    @override_settings(**TWILIO_OK)
    @twilio_simule
    def test_rejet_motif_obligatoire_et_sms(self):
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        self.assertEqual(self.client.post(f'/api/rdv/{rid}/rejeter/', {}, format='json').status_code, 400)
        r = self.client.post(f'/api/rdv/{rid}/rejeter/', {'motif': 'Pièces incomplètes'}, format='json')
        self.assertEqual((r.data['status'], r.data['sms']), ('rejected', 'envoye'))
        self.assertEqual(r.data['rdv']['motif_rejet'], 'Pièces incomplètes')
        self.assertIn('Pieces incompletes', SMSLog.objects.get().message)

    @override_settings(**TWILIO_OK)
    @twilio_simule
    def test_echec_twilio_ne_bloque_pas(self):
        self.citoyen.telephone = '770000000'   # le stub Twilio refuse ce numéro
        self.citoyen.save()
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        r = self.client.post(f'/api/rdv/{rid}/valider/')
        self.assertEqual((r.status_code, r.data['status'], r.data['sms']), (200, 'confirmed', 'echec'))
        self.assertIn('non verifie', SMSLog.objects.get().erreur)

    @override_settings(TWILIO_ACCOUNT_SID='', TWILIO_AUTH_TOKEN='', TWILIO_FROM_NUMBER='', BREVO_SMS_SENDER='',
                       SMSGATE_LOGIN='')
    def test_sans_configuration_twilio(self):
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        self.assertEqual(self.client.post(f'/api/rdv/{rid}/valider/').data['sms'], 'non_configure')
        self.assertEqual(self.client.get('/api/notifications/sms/').status_code, 200)
        self.client.force_authenticate(self.citoyen)
        self.assertEqual(self.client.get('/api/notifications/sms/').status_code, 403)

    @override_settings(SMSGATE_LOGIN='KIGI01', SMSGATE_PASSWORD='mdp-passerelle',
                       SMSGATE_URL='https://api.sms-gate.app/3rdparty/v1/message',
                       BREVO_API_KEY='cle-test', BREVO_SMS_SENDER='SunuTrib', TWILIO_ACCOUNT_SID='ACtest')
    def test_sms_par_telephone_android_prioritaire(self):
        """Passerelle gratuite par téléphone Android : utilisée avant Brevo et Twilio."""
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        reponse = mock.Mock(status_code=202, json=lambda: {'id': 'Pk3Ek', 'state': 'Pending'})
        with mock.patch('apps.notifications.sms.requests.post', return_value=reponse) as post:
            r = self.client.post(f'/api/rdv/{rid}/valider/')
        self.assertEqual(r.data['sms'], 'envoye')
        self.assertEqual(post.call_args.args[0], 'https://api.sms-gate.app/3rdparty/v1/message')
        self.assertEqual(post.call_args.kwargs['auth'], ('KIGI01', 'mdp-passerelle'))
        corps = post.call_args.kwargs['json']
        self.assertEqual(corps['phoneNumbers'], ['+221771234567'])
        self.assertIn('CONFIRME', corps['message'])
        self.assertEqual(SMSLog.objects.get().sid, 'Pk3Ek')

        # Identifiants refusés : message clair, RDV tout de même confirmé
        rid2 = self._demande(heure='10:00').data['id']
        self.client.force_authenticate(self.accueil)
        with mock.patch('apps.notifications.sms.requests.post', return_value=mock.Mock(status_code=401, text='')), \
             self.assertLogs('apps.notifications.sms', level='ERROR'):
            r = self.client.post(f'/api/rdv/{rid2}/valider/')
        self.assertEqual((r.data['status'], r.data['sms']), ('confirmed', 'echec'))
        self.assertIn('SMSGATE_LOGIN', r.data['sms_erreur'])

    @override_settings(BREVO_API_KEY='cle-test', BREVO_SMS_SENDER='SunuTrib', TWILIO_ACCOUNT_SID='',
                       SMSGATE_LOGIN='')
    def test_sms_par_brevo(self):
        rid = self._demande().data['id']
        self.client.force_authenticate(self.accueil)
        reponse = mock.Mock(status_code=201, json=lambda: {'messageId': 1511882900176220})
        with mock.patch('apps.notifications.sms.requests.post', return_value=reponse) as post:
            r = self.client.post(f'/api/rdv/{rid}/valider/')
        self.assertEqual(r.data['sms'], 'envoye')
        corps = post.call_args.kwargs['json']
        self.assertEqual((corps['sender'], corps['recipient'][:3]), ('SunuTrib', '221'))
        self.assertEqual(SMSLog.objects.get().sid, '1511882900176220')

    def test_citoyen_ne_valide_pas_et_peut_annuler(self):
        rid = self._demande().data['id']
        self.assertEqual(self.client.post(f'/api/rdv/{rid}/valider/').status_code, 403)
        r = self.client.post(f'/api/rdv/{rid}/annuler/')
        self.assertEqual(r.data['statut'], 'cancelled')
        services = self.client.get(f'/api/rdv/services/?tribunal={self.tribunal.id}').data
        self.assertEqual(services[0]['value'], 'depot_dossier')
        self.assertTrue(services[0]['bureau'])
