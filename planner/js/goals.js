/* ===== goals.js — Управление целями ===== */

const Goals = {
    init() {
        document.getElementById('addGoalBtn').addEventListener('click', () => {
            this.openModal();
        });

        document.getElementById('goalForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveFromForm();
        });

        document.getElementById('deleteGoalBtn').addEventListener('click', () => this.deleteCurrent());
    },

    async refresh() {
        const goals = await DB.getAllGoals();
        this.render(goals);
    },

    render(goals) {
        const container = document.getElementById('goalsContainer');

        if (!goals || goals.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🎯</div>
                    <div class="empty-text">Пока нет целей. Создайте первую!</div>
                </div>`;
            return;
        }

        // Сортировка: активные сначала, потом просроченные, потом выполненные
        const sorted = [...goals].sort((a, b) => {
            const statusOrder = { 'in-progress': 0, 'overdue': 1, 'completed': 2 };
            const sa = statusOrder[a.status] ?? 0;
            const sb = statusOrder[b.status] ?? 0;
            if (sa !== sb) return sa - sb;
            return (a.deadline || '').localeCompare(b.deadline || '');
        });

        container.innerHTML = sorted.map(goal => {
            const status = this._calcStatus(goal);
            const cat = CATEGORIES[goal.category] || CATEGORIES.other;

            return `
            <div class="goal-card" data-category="${goal.category}" data-goal-id="${goal.id}">
                <div class="goal-card-header">
                    <span class="goal-card-title">${Utils.escapeHtml(goal.title)}</span>
                    <span class="goal-status ${status}">${this._statusLabel(status)}</span>
                </div>
                <div class="goal-progress-bar">
                    <div class="goal-progress-fill" style="width:${goal.progress || 0}%"></div>
                </div>
                <div class="goal-card-meta">
                    <span>${Math.round(goal.progress || 0)}%</span>
                    ${goal.deadline ? `<span>📅 ${Utils.formatDateRu(goal.deadline)}</span>` : ''}
                    <span>${cat.emoji} ${cat.label}</span>
                </div>
            </div>`;
        }).join('');

        // Клик по карточке — редактирование
        container.querySelectorAll('.goal-card').forEach(card => {
            card.addEventListener('click', () => {
                this.openModal(card.dataset.goalId);
            });
        });
    },

    _calcStatus(goal) {
        if ((goal.progress || 0) >= 100) return 'completed';
        if (goal.deadline && goal.deadline < Utils.today() && (goal.progress || 0) < 100) return 'overdue';
        return 'in-progress';
    },

    _statusLabel(status) {
        const labels = { 'in-progress': 'В процессе', 'completed': 'Выполнена', 'overdue': 'Просрочена' };
        return labels[status] || status;
    },

    openModal(editId = null) {
        const modal = document.getElementById('goalModal');
        const titleEl = document.getElementById('goalModalTitle');
        const deleteBtn = document.getElementById('deleteGoalBtn');

        if (editId) {
            titleEl.textContent = 'Редактировать цель';
            deleteBtn.style.display = '';
            this._fillForm(editId);
        } else {
            titleEl.textContent = 'Новая цель';
            deleteBtn.style.display = 'none';
            this._resetForm();
        }

        modal.classList.add('active');
        document.getElementById('goalTitle').focus();
    },

    _resetForm() {
        document.getElementById('goalForm').reset();
        document.getElementById('goalId').value = '';
        document.getElementById('goalProgress').value = 0;
        document.getElementById('goalProgressValue').textContent = '0';
    },

    async _fillForm(goalId) {
        const goal = await DB.getGoal(goalId);
        if (!goal) return;

        document.getElementById('goalId').value = goal.id;
        document.getElementById('goalTitle').value = goal.title || '';
        document.getElementById('goalDeadline').value = goal.deadline || '';
        document.getElementById('goalCategory').value = goal.category || 'other';
        document.getElementById('goalProgress').value = goal.progress || 0;
        document.getElementById('goalProgressValue').textContent = Math.round(goal.progress || 0);
        document.getElementById('goalDescription').value = goal.description || '';
    },

    async saveFromForm() {
        const id = document.getElementById('goalId').value;
        const title = document.getElementById('goalTitle').value.trim();

        if (!title) {
            App.toast('Введите название цели', 'error');
            return;
        }

        const goal = {
            id: id || Utils.generateId(),
            title,
            deadline: document.getElementById('goalDeadline').value || null,
            category: document.getElementById('goalCategory').value,
            progress: parseInt(document.getElementById('goalProgress').value) || 0,
            description: document.getElementById('goalDescription').value,
            createdAt: id ? (await DB.getGoal(id))?.createdAt : new Date().toISOString(),
            updatedAt: new Date().toISOString()
        };

        // Авто-статус
        goal.status = goal.progress >= 100 ? 'completed' : 'in-progress';

        await DB.saveGoal(goal);
        document.getElementById('goalModal').classList.remove('active');
        App.toast(id ? 'Цель обновлена' : 'Цель создана', 'success');
        this.refresh();
    },

    async deleteCurrent() {
        const id = document.getElementById('goalId').value;
        if (!id) return;

        if (confirm('Удалить эту цель?')) {
            await DB.deleteGoal(id);
            document.getElementById('goalModal').classList.remove('active');
            App.toast('Цель удалена', 'success');
            this.refresh();
        }
    }
};
