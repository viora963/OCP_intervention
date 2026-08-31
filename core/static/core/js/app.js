/* ── OCP App Utilities ── */

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