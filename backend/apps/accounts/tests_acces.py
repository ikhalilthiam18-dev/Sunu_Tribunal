"""
Sécurisation de l'accès du personnel — SunuTribunal
Lancer : python manage.py test apps.accounts
"""
import re
from datetime import timedelta
from django.core import mail
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.accounts.models import User, SecuriteCompte
from apps.rdv.models import Tribunal

MSG_ECHEC = 'Email ou mot de passe incorrect.'
MSG_BLOQUE = 'Trop de tentatives. Réessayez dans 15 minutes.'


def mot_de_passe_recu():
    """Mot de passe provisoire lu dans le dernier e-mail envoyé (boîte mémoire des tests)."""
    return re.search(r'Mot de passe provisoire : (\S+)', mail.outbox[-1].body).group(1)


class AccesPersonnelTests(APITestCase):

    def setUp(self):
        cache.clear()
        self.tribunal = Tribunal.objects.create(nom='TGI Dakar', adresse='Dakar')
        self.chef = User.objects.create_user('chef@test.sn', 'motdepasse123', nom='Fall',
                                             role='admin', tribunal=self.tribunal)
        self.citoyen = User.objects.create_user('citoyen@test.sn', 'motdepasse123', nom='Diallo')

    def _login(self, email, password):
        return self.client.post('/api/auth/login/', {'email': email, 'password': password}, format='json')

    def _creer_agent(self, email='juge2@test.sn', role='juge'):
        """Crée un agent par la page Personnel ; son mot de passe provisoire arrive par e-mail."""
        self.client.force_authenticate(self.chef)
        res = self.client.post('/api/auth/staff/', {'email': email, 'nom': 'Diop', 'prenom': 'Awa',
                                                    'role': role}, format='json')
        self.client.force_authenticate(None)
        return res

    # ── 1. Formulaire de connexion unique ──────────────
    def test_formulaire_unique_renvoie_le_bon_role(self):
        self.assertEqual(self._creer_agent().status_code, 201)
        res = self._login('juge2@test.sn', mot_de_passe_recu())
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.data['user']['role'], res.data['doit_changer_mdp']), ('juge', True))
        res = self._login('citoyen@test.sn', 'motdepasse123')
        self.assertEqual((res.data['user']['role'], res.data['doit_changer_mdp']), ('citoyen', False))

    def test_meme_message_quel_que_soit_l_echec(self):
        inactif = User.objects.create_user('inactif@test.sn', 'motdepasse123', nom='X', role='juge', is_active=False)
        for email, mdp in [('citoyen@test.sn', 'mauvais'), ('inconnu@test.sn', 'motdepasse123'),
                           (inactif.email, 'motdepasse123')]:
            res = self._login(email, mdp)
            self.assertEqual((res.status_code, str(res.data['detail'])), (401, MSG_ECHEC), email)
            self.assertNotIn('user', res.data)

    def test_inscription_publique_toujours_citoyen(self):
        res = self.client.post('/api/auth/register/', {
            'email': 'pirate@test.sn', 'nom': 'Pirate', 'role': 'admin', 'tribunal': self.tribunal.id,
            'password': 'motdepasse123', 'password2': 'motdepasse123'}, format='json')
        self.assertEqual(res.status_code, 201)
        pirate = User.objects.get(email='pirate@test.sn')
        self.assertEqual((pirate.role, pirate.tribunal), ('citoyen', None))

    def test_inscription_messages_d_erreur_en_francais(self):
        def inscrire(email, mdp):
            return self.client.post('/api/auth/register/', {'email': email, 'nom': 'Ndiaye',
                                                            'password': mdp, 'password2': mdp}, format='json')
        # Validateurs Django du mot de passe, en français
        r = inscrire('awa@test.sn', 'abc')
        self.assertEqual(r.status_code, 400)
        self.assertTrue(any('trop court' in m for m in r.data['password']), r.data)
        r = inscrire('awa@test.sn', 'password')
        self.assertTrue(any('trop courant' in m for m in r.data['password']), r.data)
        r = inscrire('awa.ndiaye@test.sn', 'awa.ndiaye')
        self.assertTrue(any('semblable' in m for m in r.data['password']), r.data)
        # Email déjà utilisé (sans tenir compte des majuscules)
        r = inscrire('Citoyen@Test.sn', 'Baobab-Dakar-2026')
        self.assertEqual(r.data['email'], ['Un compte existe déjà avec cette adresse email.'])
        # Mot de passe valide : compte créé
        self.assertEqual(inscrire('awa@test.sn', 'Baobab-Dakar-2026').status_code, 201)

    # ── 2. Changement obligatoire du mot de passe ──────
    def test_changement_obligatoire_a_la_premiere_connexion(self):
        self._creer_agent()
        tmp = mot_de_passe_recu()
        jeton = self._login('juge2@test.sn', tmp).data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {jeton}')

        # Tout est bloqué côté serveur, sauf le profil et le changement de mot de passe
        res = self.client.get('/api/rdv/')
        self.assertEqual((res.status_code, res.data['code']), (403, 'changement_mdp_requis'))
        self.assertTrue(self.client.get('/api/auth/me/').data['doit_changer_mdp'])

        url = '/api/auth/changer-mot-de-passe/'
        cas_refuses = [
            ({'ancien_mdp': 'faux', 'nouveau_mdp': 'Baobab-Dakar-2026', 'confirmation': 'Baobab-Dakar-2026'}, 'ancien_mdp'),
            ({'ancien_mdp': tmp, 'nouveau_mdp': 'Baobab-Dakar-2026', 'confirmation': 'autre'}, 'confirmation'),
            ({'ancien_mdp': tmp, 'nouveau_mdp': tmp, 'confirmation': tmp}, 'nouveau_mdp'),
            ({'ancien_mdp': tmp, 'nouveau_mdp': 'Ab1-x', 'confirmation': 'Ab1-x'}, 'nouveau_mdp'),            # trop court
            ({'ancien_mdp': tmp, 'nouveau_mdp': 'password', 'confirmation': 'password'}, 'nouveau_mdp'),      # trop courant
            ({'ancien_mdp': tmp, 'nouveau_mdp': 'juge2@test.sn', 'confirmation': 'juge2@test.sn'}, 'nouveau_mdp'),  # proche de l'email
        ]
        for data, champ in cas_refuses:
            res = self.client.post(url, data, format='json')
            self.assertEqual(res.status_code, 400, data)
            self.assertIn(champ, res.data, data)

        res = self.client.post(url, {'ancien_mdp': tmp, 'nouveau_mdp': 'Baobab-Dakar-2026',
                                     'confirmation': 'Baobab-Dakar-2026'}, format='json')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertFalse(res.data['user']['doit_changer_mdp'])
        self.assertEqual(self.client.get('/api/rdv/').status_code, 200)

        self.client.credentials()
        self.assertEqual(self._login('juge2@test.sn', tmp).status_code, 401)
        self.assertFalse(self._login('juge2@test.sn', 'Baobab-Dakar-2026').data['doit_changer_mdp'])

    def test_comptes_existants_non_concernes(self):
        """Les comptes créés hors circuit (comptes de démonstration du seed) ne sont pas bloqués."""
        jeton = self._login('chef@test.sn', 'motdepasse123').data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {jeton}')
        self.assertEqual(self.client.get('/api/auth/staff/').status_code, 200)

    # ── 3. Page Personnel : jamais de greffier en chef ─
    def test_personnel_refuse_le_role_admin(self):
        res = self._creer_agent(email='chef2@test.sn', role='admin')
        self.assertEqual(res.status_code, 400)
        self.assertIn('role', res.data)
        self.assertFalse(User.objects.filter(email='chef2@test.sn').exists())

        juge = User.objects.get(pk=self._creer_agent().data['id'])
        SecuriteCompte.objects.filter(user=juge).update(doit_changer_mdp=False)
        self.client.force_authenticate(self.chef)
        res = self.client.patch(f'/api/auth/staff/{juge.id}/', {'role': 'admin'}, format='json')
        self.assertEqual(res.status_code, 400)
        juge.refresh_from_db()
        self.assertEqual(juge.role, 'juge')

        # Un autre greffier en chef ne se modifie que dans Django Admin
        chef2 = User.objects.create_user('chef2@test.sn', 'motdepasse123', nom='Ba', role='admin', tribunal=self.tribunal)
        res = self.client.patch(f'/api/auth/staff/{chef2.id}/', {'is_active': False}, format='json')
        self.assertEqual(res.status_code, 403)

        # Le chef ne peut plus fixer lui-même un mot de passe : le champ est ignoré
        avant = User.objects.get(pk=juge.pk).password
        self.client.patch(f'/api/auth/staff/{juge.id}/', {'password': 'ChoisiParLeChef26'}, format='json')
        self.assertEqual(User.objects.get(pk=juge.pk).password, avant)
        # « Renvoyer les identifiants » → nouveau mot de passe provisoire à changer de nouveau
        self.assertEqual(self.client.post(f'/api/auth/staff/{juge.id}/renvoyer/').status_code, 200)
        self.assertTrue(SecuriteCompte.de(juge).doit_changer_mdp)

    # ── 4. Blocage après 5 échecs ──────────────────────
    def test_blocage_apres_5_echecs_puis_deblocage(self):
        for _ in range(4):
            self.assertEqual(str(self._login('citoyen@test.sn', 'mauvais').data['detail']), MSG_ECHEC)
        self.assertEqual(str(self._login('citoyen@test.sn', 'mauvais').data['detail']), MSG_BLOQUE)
        # Même le bon mot de passe est refusé pendant 15 minutes
        res = self._login('citoyen@test.sn', 'motdepasse123')
        self.assertEqual((res.status_code, str(res.data['detail'])), (401, MSG_BLOQUE))

        # 15 minutes plus tard
        SecuriteCompte.objects.filter(user=self.citoyen).update(bloque_jusqua=timezone.now() - timedelta(seconds=1))
        self.assertEqual(self._login('citoyen@test.sn', 'motdepasse123').status_code, 200)
        sec = SecuriteCompte.de(self.citoyen)
        self.assertEqual((sec.echecs_connexion, sec.bloque_jusqua), (0, None))
        self.assertIsNotNone(sec.derniere_connexion_reussie)

    def test_connexion_reussie_remet_le_compteur_a_zero(self):
        for _ in range(3):
            self._login('citoyen@test.sn', 'mauvais')
        self.assertEqual(SecuriteCompte.de(self.citoyen).echecs_connexion, 3)
        self._login('citoyen@test.sn', 'motdepasse123')
        self.assertEqual(SecuriteCompte.de(self.citoyen).echecs_connexion, 0)

    def test_email_inconnu_meme_comportement(self):
        messages = [str(self._login('fantome@test.sn', 'x').data['detail']) for _ in range(6)]
        self.assertEqual(messages, [MSG_ECHEC] * 4 + [MSG_BLOQUE] * 2)

    # ── 5. Django Admin : rôle et tribunal à la création ─
    def test_django_admin_cree_un_greffier_en_chef(self):
        su = User.objects.create_superuser('root@test.sn', 'motdepasse123', nom='Root')
        self.client.force_login(su)
        page = self.client.get('/admin/accounts/user/add/').content.decode()
        self.assertIn('name="role"', page)
        self.assertIn('name="tribunal"', page)
        self.assertNotIn('name="password1"', page)      # plus aucun mot de passe à saisir

        res = self.client.post('/admin/accounts/user/add/', {
            'email': 'nouveau.chef@test.sn', 'nom': 'Sarr', 'prenom': 'Khady', 'telephone': '',
            'role': 'admin', 'tribunal': self.tribunal.id,
        })
        self.assertEqual(res.status_code, 302, res.content.decode()[:3000])
        chef = User.objects.get(email='nouveau.chef@test.sn')
        self.assertEqual((chef.role, chef.tribunal), ('admin', self.tribunal))
        self.assertTrue(SecuriteCompte.de(chef).doit_changer_mdp)
        self.assertEqual(mail.outbox[-1].to, ['nouveau.chef@test.sn'])
        self.assertEqual(self._login('nouveau.chef@test.sn', mot_de_passe_recu()).data['doit_changer_mdp'], True)

    def test_django_admin_tribunal_obligatoire_et_action_renvoyer(self):
        su = User.objects.create_superuser('root@test.sn', 'motdepasse123', nom='Root')
        self.client.force_login(su)
        res = self.client.post('/admin/accounts/user/add/', {'email': 'sans.tribunal@test.sn', 'nom': 'X',
                                                             'role': 'admin', 'tribunal': ''})
        self.assertEqual(res.status_code, 200)            # formulaire réaffiché avec l'erreur
        self.assertIn('Le tribunal est obligatoire', res.content.decode())
        self.assertFalse(User.objects.filter(email='sans.tribunal@test.sn').exists())

        juge = User.objects.create_user('juge9@test.sn', 'motdepasse123', nom='Diop', role='juge', tribunal=self.tribunal)
        res = self.client.post('/admin/accounts/user/', {'action': 'renvoyer_identifiants',
                                                         '_selected_action': [juge.id]}, follow=True)
        self.assertIn('Identifiants envoyés à juge9@test.sn', res.content.decode())
        self.assertEqual(mail.outbox[-1].subject, 'SunuTribunal — Réinitialisation de votre mot de passe')
        self.assertTrue(SecuriteCompte.de(juge).doit_changer_mdp)
