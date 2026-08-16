/* ===== stats.js — Статистика ===== */

const Stats = {
    charts: {},
    period: 'month',

    init() {
        // Период
        document.querySelectorAll('.stats-period .btn-sm').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.stats-period .btn-sm').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.period = btn.dataset.period;
                this.refresh();
            });
        });
    },

    async refresh() {
        const events = await DB.getAllEvents();
        const goals = await DB.getAllGoals();
        const notes = await DB.getAllNotes();
        const now = new Date();

        // Фильтр по периоду
        let periodStart;
        if (this.period === 'week') {
            periodStart = Utils.getWeekStart(now);
        } else if (this.period === 'month') {
            periodStart = new Date(now.getFullYear(), now.getMonth(), 1);
        } else {
            periodStart = new Date(now.getFullYear(), 0, 1);
        }
        const periodStartStr = Utils.formatDate(periodStart);

        // Считаем события за период
        const periodEvents = events.filter(ev => {
            if (ev.date >= periodStartStr) return true;
            // Повторяющиеся — проверяем хотя бы одно вхождение в период
            if (ev.repeat && ev.repeat !== 'none') {
                const todayStr = Utils.today();
                for (let d = Math.max(ev.date, periodStartStr); d <= todayStr; d = Utils.addDays(d, 1)) {
                    if (Utils.isEventOnDate(ev, d)) return true;
                }
            }
            return false;
        });

        // Обновляем карточки
        document.getElementById('statTotalEvents').textContent = periodEvents.length;

        const goalsDone = goals.filter(g => (g.progress || 0) >= 100);
        const goalsPending = goals.filter(g => (g.progress || 0) < 100);
        document.getElementById('statGoalsDone').textContent = goalsDone.length;
        document.getElementById('statGoalsPending').textContent = goalsPending.length;
        document.getElementById('statNotesCount').textContent = notes.length;

        // Рисуем графики
        this._renderCategoryChart(events);
        this._renderActivityChart(events, periodStart);
        this._renderGoalsChart(goals);
    },

    _getChartColors() {
        const isDark = document.body.dataset.theme === 'dark';
        return {
            text: isDark ? '#e2e8f0' : '#1e293b',
            grid: isDark ? '#334155' : '#e2e8f0',
            bg: isDark ? '#1e293b' : '#ffffff'
        };
    },

    _renderCategoryChart(events) {
        const ctx = document.getElementById('chartCategories');
        const colors = this._getChartColors();

        // Подсчёт по категориям
        const counts = {};
        events.forEach(ev => {
            const cat = ev.category || 'other';
            counts[cat] = (counts[cat] || 0) + 1;
        });

        const labels = Object.keys(counts).map(k => CATEGORIES[k]?.label || k);
        const data = Object.values(counts);
        const bgColors = Object.keys(counts).map(k => CATEGORIES[k]?.color || '#6b7280');

        if (this.charts.categories) this.charts.categories.destroy();

        this.charts.categories = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: bgColors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: colors.text, padding: 12 }
                    }
                }
            }
        });
    },

    _renderActivityChart(events, periodStart) {
        const ctx = document.getElementById('chartActivity');
        const colors = this._getChartColors();

        const now = new Date();
        let days;
        let labels = [];

        if (this.period === 'week') {
            days = 7;
            labels = WEEKDAYS_RU_SHORT;
        } else if (this.period === 'month') {
            days = 30;
            labels = Array.from({ length: 30 }, (_, i) => {
                const d = new Date(now);
                d.setDate(d.getDate() - 29 + i);
                return d.getDate().toString();
            });
        } else {
            days = 12;
            labels = MONTHS_RU.map(m => m.substring(0, 3).toLowerCase());
        }

        const data = [];
        for (let i = 0; i < days; i++) {
            let dateStr;
            if (this.period === 'week') {
                const d = new Date(periodStart);
                d.setDate(d.getDate() + i);
                dateStr = Utils.formatDate(d);
            } else if (this.period === 'month') {
                const d = new Date(now);
                d.setDate(d.getDate() - 29 + i);
                dateStr = Utils.formatDate(d);
            } else {
                // По месяцам — упрощённо
                data.push(events.filter(ev => {
                    if (!ev.date) return false;
                    const evMonth = Utils.parseDate(ev.date).getMonth();
                    return evMonth === i;
                }).length);
                continue;
            }

            if (dateStr) {
                const count = events.filter(ev => Utils.isEventOnDate(ev, dateStr)).length;
                data.push(count);
            } else {
                data.push(0);
            }
        }

        if (this.charts.activity) this.charts.activity.destroy();

        this.charts.activity = new Chart(ctx, {
            type: 'bar',
            data: {
                labels,
                datasets: [{
                    label: 'События',
                    data,
                    backgroundColor: 'rgba(79, 70, 229, 0.6)',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: colors.text, stepSize: 1 },
                        grid: { color: colors.grid }
                    },
                    x: {
                        ticks: { color: colors.text },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    },

    _renderGoalsChart(goals) {
        const ctx = document.getElementById('chartGoals');
        const colors = this._getChartColors();

        let completed = 0, inProgress = 0, overdue = 0;
        goals.forEach(g => {
            if ((g.progress || 0) >= 100) completed++;
            else if (g.deadline && g.deadline < Utils.today()) overdue++;
            else inProgress++;
        });

        if (this.charts.goals) this.charts.goals.destroy();

        this.charts.goals = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: ['Выполнены', 'В процессе', 'Просрочены'],
                datasets: [{
                    data: [completed, inProgress, overdue],
                    backgroundColor: ['#22c55e', '#f59e0b', '#ef4444'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: colors.text, padding: 12 }
                    }
                }
            }
        });
    }
};
