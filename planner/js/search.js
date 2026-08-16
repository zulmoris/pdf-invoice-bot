/* ===== search.js — Поиск и фильтры ===== */

const Search = {
    init() {
        const input = document.getElementById('searchInput');
        const catFilter = document.getElementById('searchCategory');
        const priorityFilter = document.getElementById('searchPriority');

        const doSearch = Utils.debounce(() => this.perform(), 200);

        input.addEventListener('input', doSearch);
        catFilter.addEventListener('change', doSearch);
        priorityFilter.addEventListener('change', doSearch);

        // Заполнить категории в фильтре (уже заполнены в HTML, но обновляем при необходимости)
    },

    async perform() {
        const query = document.getElementById('searchInput').value.trim().toLowerCase();
        const catFilter = document.getElementById('searchCategory').value;
        const priorityFilter = document.getElementById('searchPriority').value;
        const container = document.getElementById('searchResults');

        if (!query && !catFilter && !priorityFilter) {
            container.innerHTML = '<div class="search-empty">Введите запрос для поиска</div>';
            return;
        }

        const events = await DB.getAllEvents();
        const goals = await DB.getAllGoals();
        const notes = await DB.getAllNotes();
        const results = [];

        // Поиск по событиям
        events.forEach(ev => {
            if (catFilter && ev.category !== catFilter) return;
            if (priorityFilter && ev.priority !== priorityFilter) return;
            if (query) {
                const text = `${ev.title} ${ev.description || ''}`.toLowerCase();
                if (!text.includes(query)) return;
            }
            results.push({
                type: 'event',
                id: ev.id,
                title: ev.title,
                meta: `${Utils.formatDateRu(ev.date)} ${ev.timeStart ? '• ' + ev.timeStart : ''} • ${CATEGORIES[ev.category]?.label || ''}`,
                icon: '📅'
            });
        });

        // Поиск по целям
        goals.forEach(g => {
            if (catFilter && g.category !== catFilter) return;
            if (query) {
                const text = `${g.title} ${g.description || ''}`.toLowerCase();
                if (!text.includes(query)) return;
            }
            results.push({
                type: 'goal',
                id: g.id,
                title: g.title,
                meta: `${g.deadline ? Utils.formatDateRu(g.deadline) : 'Без дедлайна'} • ${Math.round(g.progress || 0)}%`,
                icon: '🎯'
            });
        });

        // Поиск по заметкам
        notes.forEach(n => {
            if (catFilter && n.category !== catFilter) return;
            if (query) {
                const text = `${n.title} ${n.content || ''}`.toLowerCase();
                if (!text.includes(query)) return;
            }
            results.push({
                type: 'note',
                id: n.id,
                title: n.title,
                meta: `${n.date ? Utils.formatDateRu(n.date) : ''} ${n.category ? '• ' + CATEGORIES[n.category]?.label : ''}`,
                icon: '📓'
            });
        });

        if (results.length === 0) {
            container.innerHTML = '<div class="search-empty">Ничего не найдено</div>';
            return;
        }

        container.innerHTML = results.map(r => `
            <div class="search-result-item" data-type="${r.type}" data-id="${r.id}">
                <span class="search-result-type">${r.icon}</span>
                <div class="search-result-info">
                    <div class="search-result-title">${Utils.escapeHtml(r.title)}</div>
                    <div class="search-result-meta">${r.meta}</div>
                </div>
            </div>
        `).join('');

        // Клик по результату
        container.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const type = item.dataset.type;
                const id = item.dataset.id;
                if (type === 'event') {
                    Events.openModal(id);
                } else if (type === 'goal') {
                    Goals.openModal(id);
                } else if (type === 'note') {
                    Notes.openModal(id);
                }
            });
        });
    }
};
