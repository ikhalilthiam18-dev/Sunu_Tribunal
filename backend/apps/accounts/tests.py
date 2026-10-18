"""
Tests de sécurité des rôles — SunuTribunal
Lancer : python manage.py test apps.accounts
"""
import datetime
import re
from django.core import mail
from rest_framework.test import APITestCase
from apps.accounts.models import User, SecuriteCompte, generer_mot_de_passe
from apps.rdv.models import Tribunal, RendezVous


def mot_de_passe_recu(index=-1):
    """Mot de passe provisoire lu dans un e-mail envoyé (les tests utilisent la boîte mémoire mail.outbox)."""
    return re.search(r'Mot de passe provisoire : (\S+)', mail.outbox[index].body).group(1)


class RolesSecuriteTests(APITestCase):

    def setUp(self):
        self.tribunal = Tribunal.objects.create(nom='TGI Dakar', adresse='Dakar')
        self.citoyen = User.objects.create_user('citoyen@test.sn', 'motdepasse123', nom='Diallo')
        self.chef = User.objects.create_user('chef@test.sn', 'motdepasse123', nom='Fall',
                                             role='admin', tribunal=self.tribunal)
        self.juge = User.objects.create_user('juge@test.sn', 'motdepasse123', nom='Diop',
                                             role='juge', tribunal=self.tribunal)

    # ── Inscription publique ────────────────────────────
    def test_inscription_force_role_citoyen(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'pirate@test.sn', 'nom': 'Pirate',
            'password': 'motdepasse123', 'password2': 'motdepasse123',
            'role': 'admin',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(User.objects.get(email='pirate@test.sn').role, 'citoyen')

    def test_me_ne_peut_pas_changer_son_role(self):
        self.client.force_authenticate(self.citoyen)
        res = self.client.patch('/api/auth/me/', {'role': 'admin', 'telephone': '770000000'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.citoyen.refresh_from_db()
        self.assertEqual(self.citoyen.role, 'citoyen')
        self.assertEqual(self.citoyen.telephone, '770000000')

    # ── Gestion du personnel ────────────────────────────
    def test_citoyen_et_juge_ne_gerent_pas_le_personnel(self):
        for u in (self.citoyen, self.juge):
            self.client.force_authenticate(u)
            self.assertEqual(self.client.get('/api/auth/staff/').status_code, 403)

    def test_chef_cree_un_greffier_qui_peut_se_connecter(self):
        self.client.force_authenticate(self.chef)
        res = self.client.post('/api/auth/staff/', {
            'email': 'greffier@test.sn', 'nom': 'Sarr', 'prenom': 'Fatou', 'role': 'greffier',
        }, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        g = User.objects.get(email='greffier@test.sn')
        self.assertEqual(g.tribunal, self.tribunal)

        self.client.force_authenticate(None)
        res = self.client.post('/api/auth/login/', {'email': 'greffier@test.sn',
                                                    'password': mot_de_passe_recu()}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['user']['role'], 'greffier')

    def test_chef_ne_peut_pas_creer_un_citoyen_via_staff(self):
        self.client.force_authenticate(self.chef)
        res = self.client.post('/api/auth/staff/', {
            'email': 'x@test.sn', 'nom': 'X', 'password': 'temp1234', 'role': 'citoyen',
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_desactivation_compte(self):
        self.client.force_authenticate(self.chef)
        res = self.client.patch(f'/api/auth/staff/{self.juge.id}/', {'is_active': False}, format='json')
        self.assertEqual(res.status_code, 200)
        self.juge.refresh_from_db()
        self.assertFalse(self.juge.is_active)
        # impossible de se désactiver soi-même
        res = self.client.patch(f'/api/auth/staff/{self.chef.id}/', {'is_active': False}, format='json')
        self.assertEqual(res.status_code, 400)

    # ── Actions réservées au personnel ──────────────────
    def test_citoyen_ne_valide_pas_son_propre_rdv(self):
        rdv = RendezVous.objects.create(citoyen=self.citoyen, tribunal=self.tribunal, service='civil',
                                        date=datetime.date(2026, 11, 2), heure=datetime.time(9, 0))
        self.client.force_authenticate(self.citoyen)
        self.assertEqual(self.client.post(f'/api/rdv/{rdv.id}/valider/').status_code, 403)
        self.client.force_authenticate(self.juge)
        self.assertEqual(self.client.post(f'/api/rdv/{rdv.id}/valider/').status_code, 200)

    def test_generation_courrier_reservee_au_personnel(self):
        self.client.force_authenticate(self.citoyen)
        res = self.client.post('/api/chatbot/generate-doc/', {'destinataire': 'A', 'motif': 'B'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_chatbot_accepte_un_token_expire(self):
        # Un token invalide ne doit pas provoquer de 401 sur l'assistant public
        self.client.credentials(HTTP_AUTHORIZATION='Bearer token-invalide')
        res = self.client.post('/api/chatbot/ask/', {'message': ''}, format='json')
        self.assertEqual(res.status_code, 400)  # 400 = message vide, donc pas de 401


class IdentifiantsParEmailTests(APITestCase):
    """Mot de passe provisoire généré par le serveur, envoyé par e-mail, à changer à la 1re connexion."""

    def setUp(self):
        self.tgi = Tribunal.objects.create(nom='TGI Dakar', adresse='Dakar')
        self.thies = Tribunal.objects.create(nom='TGI Thies', adresse='Thies')
        self.chef = User.objects.create_user('chef@test.sn', 'motdepasse123', nom='Fall', prenom='Moussa',
                                             role='admin', tribunal=self.tgi)
        self.chef_thies = User.objects.create_user('chef2@test.sn', 'motdepasse123', nom='Ba',
                                                   role='admin', tribunal=self.thies)

    def _creer(self, chef=None, **donnees):
        self.client.force_authenticate(chef or self.chef)
        res = self.client.post('/api/auth/staff/', {'email': 'awa.ndiaye@test.sn', 'nom': 'Ndiaye',
                                                    'prenom': 'Awa', 'role': 'greffier', **donnees}, format='json')
        self.client.force_authenticate(None)
        return res

    def _connexion(self, email, mdp):
        return self.client.post('/api/auth/login/', {'email': email, 'password': mdp}, format='json')

    def test_mot_de_passe_genere_robuste(self):
        mdps = {generer_mot_de_passe() for _ in range(50)}
        self.assertEqual(len(mdps), 50)                        # jamais deux fois le même
        for m in mdps:
            self.assertEqual(len(m), 12)
            self.assertTrue(re.search(r'[A-Z]', m) and re.search(r'[a-z]', m)
                            and re.search(r'\d', m) and re.search(r'[^A-Za-z0-9]', m), m)

    def test_creation_envoie_un_email_sans_mot_de_passe_dans_la_reponse(self):
        res = self._creer(tribunal=self.thies.id)              # tentative de choisir un autre tribunal
        self.assertEqual(res.status_code, 201, res.data)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ['awa.ndiaye@test.sn'])
        self.assertEqual(email.subject, "SunuTribunal — Vos identifiants d'accès à l'espace tribunal")
        mdp = mot_de_passe_recu()
        self.assertIn(mdp, email.alternatives[0][0])           # aussi dans la version HTML
        self.assertIn('Bonjour Awa Ndiaye', email.body)
        self.assertIn('Juridiction : TGI Dakar', email.body)
        self.assertIn('Compte créé par : Moussa Fall', email.body)
        # Le mot de passe n'apparaît nulle part dans la réponse de l'API
        self.assertNotIn(mdp, str(res.data))
        self.assertNotIn('password', res.data)
        self.assertTrue(res.data['email_envoye'])
        self.assertEqual(res.data['message'], 'Compte créé. Les identifiants ont été envoyés à awa.ndiaye@test.sn.')
        # Tribunal forcé à celui du créateur
        agent = User.objects.get(email='awa.ndiaye@test.sn')
        self.assertEqual(agent.tribunal, self.tgi)
        self.assertTrue(SecuriteCompte.de(agent).doit_changer_mdp)
        self.assertEqual(agent.identifiants.cree_par, self.chef)
        self.assertIsNotNone(agent.identifiants.mdp_provisoire_envoye_le)

    def test_changement_obligatoire_puis_acces(self):
        self._creer()
        mdp = mot_de_passe_recu()
        connexion = self._connexion('awa.ndiaye@test.sn', mdp)
        self.assertEqual((connexion.status_code, connexion.data['doit_changer_mdp']), (200, True))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {connexion.data['access']}")

        res = self.client.get('/api/rdv/')
        self.assertEqual((res.status_code, res.data['code']), (403, 'changement_mdp_requis'))
        self.assertEqual(self.client.get('/api/auth/me/').status_code, 200)

        url = '/api/auth/changer-mot-de-passe/'
        mauvais = self.client.post(url, {'ancien_mdp': 'faux', 'nouveau_mdp': 'Baobab-Dakar-2026',
                                         'confirmation': 'Baobab-Dakar-2026'}, format='json')
        self.assertEqual(mauvais.status_code, 400)
        self.assertIn('ancien_mdp', mauvais.data)
        identique = self.client.post(url, {'ancien_mdp': mdp, 'nouveau_mdp': mdp, 'confirmation': mdp}, format='json')
        self.assertEqual(identique.status_code, 400)
        self.assertIn('nouveau_mdp', identique.data)

        ok = self.client.post(url, {'ancien_mdp': mdp, 'nouveau_mdp': 'Baobab-Dakar-2026',
                                    'confirmation': 'Baobab-Dakar-2026'}, format='json')
        self.assertEqual((ok.status_code, ok.data['message']), (200, 'Mot de passe modifié.'))
        self.assertEqual(self.client.get('/api/rdv/').status_code, 200)
        agent = User.objects.get(email='awa.ndiaye@test.sn')
        self.assertFalse(SecuriteCompte.de(agent).doit_changer_mdp)
        self.assertIsNotNone(agent.identifiants.mdp_change_le)

    def test_renvoyer_les_identifiants(self):
        agent_id = self._creer().data['id']
        ancien = mot_de_passe_recu()
        self.client.force_authenticate(self.chef)
        res = self.client.post(f'/api/auth/staff/{agent_id}/renvoyer/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].subject, 'SunuTribunal — Réinitialisation de votre mot de passe')
        nouveau = mot_de_passe_recu()
        self.assertNotEqual(nouveau, ancien)
        self.assertNotIn(nouveau, str(res.data))
        self.client.force_authenticate(None)
        self.assertEqual(self._connexion('awa.ndiaye@test.sn', ancien).status_code, 401)   # l'ancien ne marche plus
        res = self._connexion('awa.ndiaye@test.sn', nouveau)
        self.assertEqual((res.status_code, res.data['doit_changer_mdp']), (200, True))

    def test_chef_d_un_autre_tribunal_ne_peut_pas_renvoyer(self):
        agent_id = self._creer().data['id']
        self.client.force_authenticate(self.chef_thies)
        self.assertEqual(self.client.post(f'/api/auth/staff/{agent_id}/renvoyer/').status_code, 404)
        self.assertEqual(len(mail.outbox), 1)                   # aucun nouvel e-mail
        # Un chef ne réinitialise pas non plus un autre greffier en chef
        self.client.force_authenticate(self.chef)
        chef_bis = User.objects.create_user('chef3@test.sn', 'motdepasse123', nom='Sy', role='admin', tribunal=self.tgi)
        self.assertEqual(self.client.post(f'/api/auth/staff/{chef_bis.id}/renvoyer/').status_code, 403)

    def test_echec_d_envoi_ne_bloque_pas_la_creation(self):
        from unittest import mock
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=ConnectionError('smtp down')), \
             self.assertLogs('apps.accounts.emails', level='ERROR'):
            res = self._creer()
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data['email_envoye'])
        self.assertIn('injoignable', res.data['email_erreur'])
        self.assertIn('Renvoyer les identifiants', res.data['message'])
        self.assertTrue(User.objects.filter(email='awa.ndiaye@test.sn').exists())

    def test_production_sans_service_email_echec_visible(self):
        from django.test import override_settings
        with override_settings(EMAIL_BACKEND='apps.accounts.brevo.SansServiceEmailBackend'), \
             self.assertLogs('apps.accounts.emails', level='ERROR'):
            res = self._creer()
        self.assertEqual(res.status_code, 201)
        self.assertFalse(res.data['email_envoye'])
        self.assertIn('BREVO_API_KEY', res.data['email_erreur'])
        self.assertIn('Renvoyer les identifiants', res.data['message'])
        self.assertEqual(len(mail.outbox), 0)

    def test_echec_du_renvoi_garde_l_ancien_mot_de_passe(self):
        from unittest import mock
        agent_id = self._creer().data['id']
        ancien = mot_de_passe_recu()
        self.client.force_authenticate(self.chef)
        with mock.patch('django.core.mail.EmailMultiAlternatives.send', side_effect=ConnectionError('smtp down')), \
             self.assertLogs('apps.accounts.emails', level='ERROR'):
            res = self.client.post(f'/api/auth/staff/{agent_id}/renvoyer/')
        self.assertFalse(res.data['email_envoye'])
        self.client.force_authenticate(None)
        # Personne ne se retrouve avec un mot de passe inconnu : l'ancien fonctionne toujours
        self.assertEqual(self._connexion('awa.ndiaye@test.sn', ancien).status_code, 200)


class BrevoBackendTests(APITestCase):
    """Envoi par l'API web Brevo (requête HTTP simulée : aucun e-mail réel)."""

    def _message(self):
        from django.core.mail import EmailMultiAlternatives
        m = EmailMultiAlternatives('Objet', 'Texte', 'SunuTribunal <greffe@test.sn>', ['awa@test.sn'])
        m.attach_alternative('<p>HTML</p>', 'text/html')
        return m

    def test_envoi_appelle_l_api_avec_texte_et_html(self):
        from unittest import mock
        from apps.accounts.brevo import BrevoEmailBackend, URL_API
        with self.settings(BREVO_API_KEY='cle-test'), \
             mock.patch('apps.accounts.brevo.requests.post', return_value=mock.Mock(status_code=201)) as post:
            self.assertEqual(BrevoEmailBackend().send_messages([self._message()]), 1)
        args, kwargs = post.call_args
        self.assertEqual(args[0], URL_API)
        self.assertEqual(kwargs['headers']['api-key'], 'cle-test')
        self.assertEqual(kwargs['json']['sender'], {'name': 'SunuTribunal', 'email': 'greffe@test.sn'})
        self.assertEqual(kwargs['json']['to'], [{'email': 'awa@test.sn'}])
        self.assertEqual(kwargs['json']['htmlContent'], '<p>HTML</p>')

    def test_cle_refusee_donne_un_message_lisible(self):
        from unittest import mock
        from apps.accounts.brevo import BrevoEmailBackend, ErreurBrevo
        from apps.accounts.emails import _message_erreur
        reponse = mock.Mock(status_code=401, text='{"code":"unauthorized"}')
        with self.settings(BREVO_API_KEY='mauvaise'), \
             mock.patch('apps.accounts.brevo.requests.post', return_value=reponse), \
             self.assertRaises(ErreurBrevo) as ctx:
            BrevoEmailBackend().send_messages([self._message()])
        self.assertIn('BREVO_API_KEY', _message_erreur(ctx.exception))
