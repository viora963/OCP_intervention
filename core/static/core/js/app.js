/* ── OCP App Utilities ── */

function getCookie(name) {
    const match = document.cookie.match('(^|;\\s*)(' + name + ')=([^;]*)');
    return match ? decodeURIComponent(match[3]) : null;
}

document.addEventListener('alpine:init', () => {
    Alpine.data('toastSystem', () => ({
        toasts: [],
        add(message, type = 'info') {
            const id = Date.now();
            this.toasts.push({ id, message, type });
            setTimeout(() => this.remove(id), 4000);
        },
        remove(id) {
            this.toasts = this.toasts.filter(t => t.id !== id);
        }
    }));

    // Recherche globale du top bar — interroge /recherche/?q=... (débounce
    // 300ms) et affiche les résultats groupés par catégorie (interventions,
    // clients, techniciens, pièces) dans un menu déroulant sous le champ.
    Alpine.data('globalSearch', () => ({
        q: '',
        open: false,
        loading: false,
        results: { interventions: [], clients: [], techniciens: [], pieces: [] },
        _debounce: null,

        onInput() {
            clearTimeout(this._debounce);
            if (this.q.trim().length < 2) {
                this.results = { interventions: [], clients: [], techniciens: [], pieces: [] };
                this.open = false;
                return;
            }
            this._debounce = setTimeout(() => this._search(), 300);
        },

        async _search() {
            this.loading = true;
            try {
                const res = await fetch(`/recherche/ajax/?q=${encodeURIComponent(this.q)}`, {
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                });
                if (!res.ok) return;
                this.results = await res.json();
                this.open = true;
            } catch (e) {
                console.error('Recherche globale : échec', e);
            } finally {
                this.loading = false;
            }
        },

        get hasResults() {
            return Object.values(this.results).some(arr => arr.length > 0);
        },
    }));

    // Partage de position — tout le personnel (techniciens, agents bureau,
    // managers) peut activer/désactiver ce toggle depuis la sidebar (voir
    // _sidebar.html). Tant qu'il est actif, la position du navigateur est
    // renvoyée périodiquement à /position/partager/ ; l'admin la voit sur
    // /suivi/ et le dashboard. Le choix est mémorisé (localStorage) pour
    // reprendre automatiquement le partage à la navigation suivante — mais
    // JAMAIS activé par défaut : c'est toujours un opt-in explicite de
    // l'utilisateur, jamais présumé.
    //
    // NOTE : l'API de géolocalisation exige un contexte sécurisé (HTTPS, ou
    // localhost). Sur un déploiement en simple HTTP, le navigateur refuse
    // silencieusement — d'où la vérification explicite `isSecureContext`
    // ci-dessous, avec un message clair plutôt qu'un échec muet.
    Alpine.data('positionSharing', () => ({
        sharing: localStorage.getItem('ocp_position_sharing') === '1',
        loading: false,
        error: null,
        accuracy: null,
        _intervalId: null,

        // NOTE : ne PAS aussi appeler `x-init="init()"` sur l'élément —
        // Alpine appelle automatiquement une méthode nommée `init()`
        // définie dans un composant Alpine.data ; l'appeler une seconde
        // fois via x-init la déclenchait deux fois (double intervalle).
        init() {
            if (this.sharing) this._start();
        },

        toggle() {
            if (this.loading) return;
            if (this.sharing) {
                this._stop(true);
            } else {
                this._requestAndStart();
            }
        },

        _requestAndStart() {
            this.error = null;
            if (!window.isSecureContext) {
                this.error = "Le partage de position nécessite une connexion sécurisée (HTTPS).";
                return;
            }
            if (!('geolocation' in navigator)) {
                this.error = "La géolocalisation n'est pas disponible sur ce navigateur.";
                return;
            }
            this.loading = true;
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.loading = false;
                    this.sharing = true;
                    this.accuracy = Math.round(pos.coords.accuracy);
                    localStorage.setItem('ocp_position_sharing', '1');
                    this._start();
                },
                (err) => {
                    this.loading = false;
                    this.error = err.code === 1
                        ? "Position refusée. Autorisez la géolocalisation dans les réglages du navigateur."
                        : "Position indisponible pour le moment.";
                },
                { enableHighAccuracy: true, timeout: 10000 }
            );
        },

        _start() {
            this.error = null;
            this._sendPosition();
            // Renvoie la position toutes les 30s tant que l'onglet est actif.
            this._intervalId = setInterval(() => this._sendPosition(), 30000);
        },

        _stop(notifyServer) {
            this.sharing = false;
            this.accuracy = null;
            localStorage.removeItem('ocp_position_sharing');
            if (this._intervalId) { clearInterval(this._intervalId); this._intervalId = null; }
            if (notifyServer) {
                fetch('/position/arreter/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCookie('csrftoken') },
                });
            }
        },

        // NOTE : la précision (pos.coords.accuracy, en mètres) vient
        // directement du navigateur — c'est lui qui choisit sa source
        // (GPS, Wi-Fi, ou IP en dernier recours sur un ordinateur sans
        // puce GPS). Une précision de plusieurs dizaines de km n'est PAS
        // un bug de l'appli : c'est le navigateur qui situe mal l'appareil
        // faute de GPS. On l'affiche pour que ce soit visible plutôt que
        // de laisser deviner pourquoi le point semble "faux".
        _sendPosition() {
            if (!window.isSecureContext || !('geolocation' in navigator)) return;
            navigator.geolocation.getCurrentPosition(
                (pos) => {
                    this.accuracy = Math.round(pos.coords.accuracy);
                    fetch('/position/partager/', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCookie('csrftoken'),
                        },
                        body: JSON.stringify({
                            latitude: pos.coords.latitude,
                            longitude: pos.coords.longitude,
                        }),
                    }).catch((e) => console.error('Partage de position : échec envoi', e));
                },
                (err) => console.warn('Partage de position : géolocalisation refusée', err),
                { enableHighAccuracy: true, timeout: 10000 }
            );
        },
    }));
});

// Auto-hide Django messages after 5s
document.addEventListener('DOMContentLoaded', () => {
    const msgs = document.querySelectorAll('.django-msg');
    msgs.forEach(m => {
        setTimeout(() => {
            m.style.opacity = '0';
            m.style.transform = 'translateY(-10px)';
            setTimeout(() => m.remove(), 300);
        }, 5000);
    });
});