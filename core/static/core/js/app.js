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
