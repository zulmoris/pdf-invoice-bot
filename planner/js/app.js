/* ===== app.js — Главный модуль ===== */

const App = {
    currentView: 'calendar',

    async init() {
        try {
            // Инициализация БД
            await DB.init();

            // Инициализация модулей
            Calendar.init();
            Events.init();
            Goals.init();
            Notes.init();
            Search.init();
            Notifications.init();
            Stats.init();

            // Навигация
            this._bindNavigation();
            this._bindCalendarNav();
            this._bindExportImport();
            this._bindTheme();

            // Загрузить тему
            const savedTheme = await DB.getSetting('theme');
            if (savedTheme) {
                document.body.dataset.theme = savedTheme;
            }

            // Загрузить цели и заметки
            Goals.refresh();
            Notes.refresh();

            // Синхронизация (после загрузки всех модулей)
            if (typeof Sync !== 'undefined') {
                await Sync.init();
            }

            // Запланировать уведомления
            Notifications.scheduleAll();

            // Проверять уведомления каждую минуту
            setInterval(() => Notifications.scheduleAll(), 60000);

            // Service Worker
            this._registerSW();

            console.log('Планировщик загружен');
        } catch (err) {
            console.error('Ошибка инициализации:', err);
            this.toast('Ошибка загрузки приложения', 'error');
        }
    },

    _bindNavigation() {
        // Sidebar nav
        document.querySelectorAll('.sidebar .nav-item[data-view]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchView(btn.dataset.view);
                this._closeSidebar();
            });
        });

        // Bottom nav
        document.querySelectorAll('.bottom-nav-item[data-view]').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchView(btn.dataset.view);
            });
        });

        // Sidebar toggle
        document.getElementById('menuBtn').addEventListener('click', () => this._openSidebar());
        document.getElementById('sidebarClose').addEventListener('click', () => this._closeSidebar());
        document.getElementById('sidebarOverlay').addEventListener('click', () => this._closeSidebar());

        // Сегодня
        document.getElementById('todayBtn').addEventListener('click', () => {
            Calendar.goToToday();
        });
    },

    _bindCalendarNav() {
        document.getElementById('prevBtn').addEventListener('click', () => Calendar.navigate(-1));
        document.getElementById('nextBtn').addEventListener('click', () => Calendar.navigate(1));

        // Переключение вида
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                Calendar.setViewMode(btn.dataset.viewmode);
            });
        });

        // Свайпы для мобильных
        let touchStartX = 0;
        const calContainer = document.getElementById('calendarContainer');
        calContainer.addEventListener('touchstart', (e) => {
            touchStartX = e.touches[0].clientX;
        }, { passive: true });
        calContainer.addEventListener('touchend', (e) => {
            const diff = touchStartX - e.changedTouches[0].clientX;
            if (Math.abs(diff) > 60) {
                Calendar.navigate(diff > 0 ? 1 : -1);
            }
        }, { passive: true });
    },

    _bindExportImport() {
        document.getElementById('btnExport').addEventListener('click', async () => {
            try {
                const data = await DB.exportAll();
                const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `planner-backup-${Utils.today()}.json`;
                a.click();
                URL.revokeObjectURL(url);
                this.toast('Данные экспортированы', 'success');
                this._closeSidebar();
            } catch (err) {
                this.toast('Ошибка экспорта', 'error');
            }
        });

        document.getElementById('btnImport').addEventListener('click', () => {
            document.getElementById('importFile').click();
        });

        document.getElementById('importFile').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            try {
                const text = await file.text();
                const data = JSON.parse(text);
                await DB.importAll(data);
                this.toast('Данные импортированы!', 'success');
                Calendar.refresh();
                Goals.refresh();
                Notes.refresh();
            } catch (err) {
                this.toast('Ошибка импорта: неверный формат файла', 'error');
            }

            e.target.value = ''; // Сброс
            this._closeSidebar();
        });
    },

    async _bindTheme() {
        document.getElementById('btnToggleTheme').addEventListener('click', async () => {
            const current = document.body.dataset.theme;
            const next = current === 'light' ? 'dark' : 'light';
            document.body.dataset.theme = next;
            await DB.saveSetting('theme', next);
            this._closeSidebar();

            // Обновить мета theme-color
            const meta = document.querySelector('meta[name="theme-color"]');
            if (meta) {
                meta.content = next === 'dark' ? '#0f172a' : '#4f46e5';
            }

            // Перерисовать статистику с новыми цветами
            if (this.currentView === 'stats') {
                Stats.refresh();
            }
        });
    },

    switchView(view) {
        this.currentView = view;

        // Скрыть все views
        document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
        document.getElementById(`view${view.charAt(0).toUpperCase() + view.slice(1)}`).classList.add('active');

        // Обновить навигацию
        document.querySelectorAll('.nav-item[data-view]').forEach(n => {
            n.classList.toggle('active', n.dataset.view === view);
        });
        document.querySelectorAll('.bottom-nav-item[data-view]').forEach(n => {
            n.classList.toggle('active', n.dataset.view === view);
        });

        // Обновить заголовок
        const titles = {
            calendar: 'Календарь',
            goals: 'Цели',
            notes: 'Заметки',
            stats: 'Статистика',
            search: 'Поиск'
        };
        document.getElementById('headerTitle').textContent = titles[view] || view;

        // Показать/скрыть календарную навигацию
        const calNav = document.getElementById('calendarNav');
        calNav.style.display = view === 'calendar' ? '' : 'none';

        // Обновить данные для view
        if (view === 'goals') Goals.refresh();
        if (view === 'notes') Notes.refresh();
        if (view === 'stats') Stats.refresh();
        if (view === 'calendar') Calendar.refresh();
        if (view === 'search') document.getElementById('searchInput').focus();
    },

    _openSidebar() {
        document.getElementById('sidebar').classList.add('open');
        document.getElementById('sidebarOverlay').classList.add('active');
    },

    _closeSidebar() {
        document.getElementById('sidebar').classList.remove('open');
        document.getElementById('sidebarOverlay').classList.remove('active');
    },

    _registerSW() {
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('sw.js').catch(err => {
                console.warn('SW registration failed:', err);
            });
        }
    },

    /** Показать toast-уведомление */
    toast(message, type = 'success') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Запуск
document.addEventListener('DOMContentLoaded', () => App.init());
