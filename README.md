<hr>

<div align="center">

<h1 align="center">Intervia — Gestion des Interventions OCP Khouribga</h1>

</div>

<pre align="center">Une plateforme Django qui gère l'ensemble du cycle de vie d'une intervention de maintenance pour OCP Khouribga — de la demande à l'assignation intelligente d'un technicien, en passant par le suivi en temps réel, la gestion du stock, la génération de rapports et le retour client.</pre>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-4.2-092E20?logo=django&logoColor=white">
  <img alt="Tailwind CSS" src="https://img.shields.io/badge/Tailwind_CSS-3.4-38B2AC?logo=tailwindcss&logoColor=white">
  <img alt="Alpine.js" src="https://img.shields.io/badge/Alpine.js-UI-8BC0D0?logo=alpinedotjs&logoColor=black">
  <img alt="Chart.js" src="https://img.shields.io/badge/Chart.js-Graphiques-FF6384?logo=chartdotjs&logoColor=white">
  <img alt="xhtml2pdf" src="https://img.shields.io/badge/xhtml2pdf-Export_PDF-D14836?logo=adobeacrobatreader&logoColor=white">
  <img alt="Statut" src="https://img.shields.io/badge/statut-projet_de_stage-lightgrey">
  <a href="https://nasa-ammos.github.io/slim/"><img alt="SLIM" src="https://img.shields.io/badge/Bonnes%20pratiques%20issues%20de-SLIM-blue"></a>
</p>

Intervia a été développé dans le cadre d'un stage d'ingénierie logicielle au sein du service informatique du Groupe OCP, site de Khouribga, pour répondre à un besoin opérationnel concret : les agents bureau, les techniciens et les clients devaient coordonner les interventions de maintenance avec trop peu de visibilité sur le travail des autres. L'application donne à chacun une vue dédiée — les agents bureau planifient et assignent, les techniciens travaillent à partir d'une file d'attente en direct de ce qui leur est propre, et les clients peuvent suivre l'avancement de leur propre demande et évaluer le travail une fois terminé — tandis qu'un moteur de règles métier gère les recommandations de techniciens et la détection d'anomalies dans les rapports, sans recourir à un modèle entraîné.

---

## Fonctionnalités

* **Interventions** avec un cycle de statut clair (en attente → planifiée → en cours → terminée/annulée) et démarrage/fin en un clic pour le technicien assigné
* **Assignation intelligente de technicien** — un moteur de scoring combinant disponibilité, spécialité, charge de travail actuelle et proximité géographique, calculé en direct avant même l'enregistrement de l'intervention
* **Gestion du stock de pièces détachées** — chaque mouvement tracé via une couche de service unique, avec alertes de seuil bas
* **Page de suivi en temps réel** — compteurs et statuts en direct par polling (pas de WebSockets)
* **Deux tableaux de bord** — un opérationnel pour les agents bureau/managers, un personnel pour les techniciens de terrain
* **Portail client** — strictement limité aux interventions du client concerné, avec messagerie intégrée et évaluations post-intervention qui alimentent en retour le scoring des techniciens
* **Export PDF des rapports** et détection d'anomalies par règles métier (explicitement sans machine learning)
* **RBAC** via les Groupes/Permissions Django, complété par des règles d'accès *object-level*, et protection contre les attaques par force brute sur la connexion

## Sommaire

* [Démarrage rapide](#démarrage-rapide)
* [Rôles et permissions](#rôles-et-permissions)
* [Notes d'architecture](#notes-darchitecture)
* [Questions fréquentes (FAQ)](#questions-fréquentes-faq)
* [Contribuer](#contribuer)
* [Licence](#licence)
* [Support](#support)

## Démarrage rapide

### Prérequis

* Python 3.10+
* Node.js + npm (pour la compilation du CSS Tailwind)
* pip / un outil d'environnement virtuel

### Installation

1. Cloner le dépôt et s'y placer :
   ```bash
   git clone <url-du-depot>
   cd <nom-du-projet>
   ```
2. Créer et activer un environnement virtuel :
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows : venv\Scripts\activate
   ```
3. Installer les dépendances Python :
   ```bash
   pip install -r requirements.txt
   ```
4. Copier `env.example` vers `.env` et définir `SECRET_KEY`, `DEBUG` et `ALLOWED_HOSTS`.
5. Appliquer les migrations et provisionner les rôles :
   ```bash
   python manage.py migrate
   python manage.py setup_roles
   ```
6. Créer un compte administrateur :
   ```bash
   python manage.py createsuperuser
   ```
7. Compiler le CSS Tailwind une première fois (et à chaque nouvelle classe Tailwind) :
   ```bash
   cd frontend
   npm install
   npm run build:css
   cd ..
   ```

### Lancement

1. Démarrer le serveur de développement :
   ```bash
   python manage.py runserver
   ```
2. Se rendre sur `http://127.0.0.1:8000/` et se connecter avec le compte superuser, ou avec un compte `Client`/`Technician` lié à un `User` via `/admin/`.

### Exemples d'utilisation

* **Créer une intervention en tant qu'agent bureau** — le panneau de recommandation de technicien apparaît en direct dès la saisie du type, de la priorité et de la localisation, avant même l'enregistrement.
* **Travailler en tant que technicien** — le tableau de bord personnel n'affiche que les interventions assignées ; une tâche se fait avancer dans son cycle de statut en un clic, et un incident terrain peut être signalé directement en cas de problème sur site.
* **Tout suivre en direct** — la page `/suivi/` offre un tableau de bord par polling des interventions actives, de la disponibilité des techniciens et des incidents non résolus.
* **En tant que client** — le portail client permet de suivre l'avancement de son intervention, d'échanger avec l'équipe par messagerie, et de noter le technicien une fois le travail terminé.

### Build

En développement, `npm run watch:css` (depuis `frontend/`) recompile automatiquement le CSS à chaque modification de template. Il n'existe pas encore de pipeline CI qui régénère `tailwind-built.css` au déploiement — un `npm run build:css` manuel est donc nécessaire après toute modification de classes avant mise en production.

### Tests

Aucune suite de tests automatisés n'existe pour l'instant (voir [Notes d'architecture](#notes-darchitecture) ci-dessous). La vérification se fait manuellement en parcourant les flux de chaque rôle (agent bureau, technicien, manager, client) sur un jeu de données de démonstration :
```bash
python manage.py seed_demo
```

## Rôles et permissions

| Rôle | Portée |
|---|---|
| **Agent bureau** | Gestion complète : clients, techniciens, interventions, stock, rapports, statistiques, journal d'activité |
| **Technicien** | Lecture des référentiels partagés ; écriture restreinte à ses propres interventions assignées |
| **Manager** | Lecture seule sur l'ensemble du système (supervision) |
| **Client (portail)** | Ses propres interventions uniquement, plus la messagerie associée et l'évaluation post-intervention |

## Notes d'architecture

* `StockService` est la source unique de vérité pour les quantités de stock — jamais de modification directe via un formulaire.
* Le scoring des techniciens et la détection d'anomalies dans les rapports reposent sur des règles métier explicites et pondérées, pas sur du machine learning (les champs nommés `ai_*` sont conservés uniquement pour compatibilité).
* Le suivi en temps réel utilise le polling (rafraîchissement toutes les 8 secondes) plutôt que les WebSockets, pour privilégier la simplicité de déploiement.
* Les vérifications d'accès *object-level* sont centralisées dans `core/permissions.py` plutôt que dupliquées dans chaque vue.
* **Reste à faire** : tests automatisés (priorité : `StockService` et le moteur de scoring), notifications push, historique complet des évaluations clients sur la fiche technicien, export des statistiques en PDF/Excel.

## Questions fréquentes (FAQ)

1. **Pourquoi pas de machine learning pour l'assignation des techniciens ?**
   - Le besoin exigeait des décisions explicables et auditables sur un jeu de données restreint — un moteur de règles pondérées (`utils.py`) répond à cela sans la lourdeur ni l'opacité d'un modèle entraîné.
2. **Pourquoi le polling plutôt que les WebSockets pour le suivi en temps réel ?**
   - Plus simple à déployer et à maintenir à l'échelle de ce projet ; un rafraîchissement toutes les 8 secondes suffisait au besoin opérationnel.
3. **Un technicien peut-il voir les interventions d'un autre technicien ?**
   - Non — les vérifications de permission *object-level* dans `core/permissions.py` restreignent chaque technicien à ses propres interventions assignées.

## Contribuer

Ce projet est un travail académique de fin de stage (Génie Informatique, ENSA Khouribga) réalisé pour le site de Khouribga du Groupe OCP. Il n'est pas conçu comme un projet open-source public avec un processus de contribution externe, mais les retours des encadrants et évaluateurs sont les bienvenus — n'hésitez pas à ouvrir une issue ou à contacter directement le porteur du projet.

## Licence

Ce projet a été développé à des fins académiques et d'évaluation interne dans le cadre d'un stage au sein du Groupe OCP. Aucune licence open-source n'est actuellement associée ; merci de contacter le porteur du projet avant toute réutilisation ou redistribution.

## Support

Pour toute question sur ce projet, merci de contacter directement le porteur du projet.