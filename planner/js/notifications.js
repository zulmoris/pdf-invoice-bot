/* ===== notifications.js — Web Notifications ===== */

const Notifications = {
    permission: 'default',
    reminderTimers: [],

    init() {
        this.permission = Notification?.permission || 'denied';

        // Запросить разрешение при первом взаимодействии
        const requestPermission = () => {
            if ('Notification' in window && this.permission === 'default') {
                Notification.requestPermission().then(p => {
                    this.permission = p;
                });
            }
            document.removeEventListener('click', requestPermission);
        };
        document.addEventListener('click', requestPermission, { once: true });
    },

    /** Запланировать напоминание для события */
    scheduleReminder(event) {
        if (!event.date || !event.timeStart || event.reminder === 'none') return;
        if (!('Notification' in window) || this.permission !== 'granted') return;

        const reminderMinutes = parseInt(event.reminder);
        const eventTime = new Date(`${event.date}T${event.timeStart}`);
        const reminderTime = new Date(eventTime.getTime() - reminderMinutes * 60000);
        const now = new Date();

        if (reminderTime <= now) return; // Уже прошло

        const delay = reminderTime - now;

        const timer = setTimeout(() => {
            this._show(event.title, `Через ${reminderMinutes} мин: ${event.timeStart}`, event);
        }, delay);

        this.reminderTimers.push({ eventId: event.id, timer });
    },

    /** Перепланировать все напоминания (при загрузке) */
    async scheduleAll() {
        // Очистить старые
        this.reminderTimers.forEach(t => clearTimeout(t.timer));
        this.reminderTimers = [];

        if (!('Notification' in window) || this.permission !== 'granted') return;

        const events = await DB.getAllEvents();
        events.forEach(ev => this.scheduleReminder(ev));
    },

    /** Показать уведомление */
    _show(title, body, data = null) {
        try {
            const n = new Notification(title, {
                body,
                icon: 'icons/icon-192.png',
                tag: data?.id || undefined,
                requireInteraction: true
            });

            n.onclick = () => {
                window.focus();
                if (data?.id) {
                    Events.openModal(data.id);
                }
                n.close();
            };

            // Автозакрытие через 10 секунд
            setTimeout(() => n.close(), 10000);
        } catch (e) {
            console.warn('Notification failed:', e);
        }
    },

    /** Запрос разрешения вручную */
    async requestPermission() {
        if (!('Notification' in window)) {
            App.toast('Уведомления не поддерживаются в этом браузере', 'warning');
            return false;
        }
        const result = await Notification.requestPermission();
        this.permission = result;
        if (result === 'granted') {
            App.toast('Уведомления включены!', 'success');
            this.scheduleAll();
            return true;
        }
        App.toast('Уведомления отключены', 'warning');
        return false;
    }
};
