/* ===== utils.js — Хелперы ===== */

const MONTHS_RU = [
    'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
    'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
];

const MONTHS_RU_GENITIVE = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
];

const WEEKDAYS_RU_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const WEEKDAYS_RU_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

const CATEGORIES = {
    work:     { label: 'Работа',   emoji: '💼', color: '#3b82f6' },
    personal: { label: 'Личное',   emoji: '🏠', color: '#8b5cf6' },
    health:   { label: 'Здоровье', emoji: '❤️', color: '#ef4444' },
    study:    { label: 'Учёба',    emoji: '📚', color: '#f59e0b' },
    finance:  { label: 'Финансы',  emoji: '💰', color: '#22c55e' },
    other:    { label: 'Другое',   emoji: '📌', color: '#6b7280' }
};

const PRIORITIES = {
    high:   { label: 'Высокий', emoji: '🔴' },
    medium: { label: 'Средний', emoji: '🟡' },
    low:    { label: 'Низкий',  emoji: '🟢' }
};

const Utils = {
    /** Формат даты в YYYY-MM-DD */
    formatDate(date) {
        const y = date.getFullYear();
        const m = String(date.getMonth() + 1).padStart(2, '0');
        const d = String(date.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    },

    /** Парс строки YYYY-MM-DD в Date (local) */
    parseDate(str) {
        const [y, m, d] = str.split('-').map(Number);
        return new Date(y, m - 1, d);
    },

    /** Сегодня в YYYY-MM-DD */
    today() {
        return this.formatDate(new Date());
    },

    /** "14 августа 2026" */
    formatDateRu(dateStr) {
        const d = this.parseDate(dateStr);
        return `${d.getDate()} ${MONTHS_RU_GENITIVE[d.getMonth()]} ${d.getFullYear()}`;
    },

    /** "Понедельник, 14 августа 2026" */
    formatDateFullRu(dateStr) {
        const d = this.parseDate(dateStr);
        const wd = (d.getDay() + 6) % 7; // Пн=0
        return `${WEEKDAYS_RU_FULL[wd]}, ${d.getDate()} ${MONTHS_RU_GENITIVE[d.getMonth()]} ${d.getFullYear()}`;
    },

    /** "Август 2026" */
    formatMonthYear(date) {
        return `${MONTHS_RU[date.getMonth()]} ${date.getFullYear()}`;
    },

    /** Добавить дни к дате (строка YYYY-MM-DD) */
    addDays(dateStr, days) {
        const d = this.parseDate(dateStr);
        d.setDate(d.getDate() + days);
        return this.formatDate(d);
    },

    /** Разница в днях между двумя датами (строки) */
    daysDiff(dateStr1, dateStr2) {
        const d1 = this.parseDate(dateStr1);
        const d2 = this.parseDate(dateStr2);
        return Math.round((d2 - d1) / (1000 * 60 * 60 * 24));
    },

    /** Начало недели (Пн) для даты */
    getWeekStart(date) {
        const d = new Date(date);
        const day = d.getDay();
        const diff = d.getDate() - day + (day === 0 ? -6 : 1);
        d.setDate(diff);
        d.setHours(0, 0, 0, 0);
        return d;
    },

    /** Получить все даты недели */
    getWeekDates(date) {
        const start = this.getWeekStart(date);
        const dates = [];
        for (let i = 0; i < 7; i++) {
            const d = new Date(start);
            d.setDate(d.getDate() + i);
            dates.push(this.formatDate(d));
        }
        return dates;
    },

    /** День недели (0=Пн ... 6=Вс) */
    getWeekday(dateStr) {
        const d = this.parseDate(dateStr);
        return (d.getDay() + 6) % 7;
    },

    /** Проверка, событие происходит в этот день (с учётом повторений) */
    isEventOnDate(event, dateStr) {
        const eventDate = event.date;
        if (eventDate === dateStr) return true;

        // Многодневное событие
        if (event.endDate && event.endDate >= dateStr && event.date <= dateStr) return true;

        // Повторяющиеся события
        if (event.repeat && event.repeat !== 'none') {
            const ev = this.parseDate(eventDate);
            const check = this.parseDate(dateStr);

            // Не повторять события в прошлом до даты начала
            if (check < ev) return false;

            switch (event.repeat) {
                case 'daily':
                    return true;
                case 'weekly':
                    return this.getWeekday(eventDate) === this.getWeekday(dateStr);
                case 'monthly':
                    return ev.getDate() === check.getDate();
                case 'yearly':
                    return ev.getDate() === check.getDate() && ev.getMonth() === check.getMonth();
            }
        }
        return false;
    },

    /** Генерация уникального ID */
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
    },

    /** Категория: полное название */
    getCategoryLabel(key) {
        return CATEGORIES[key] ? `${CATEGORIES[key].emoji} ${CATEGORIES[key].label}` : key;
    },

    /** Приоритет: полное название */
    getPriorityLabel(key) {
        return PRIORITIES[key] ? `${PRIORITIES[key].emoji} ${PRIORITIES[key].label}` : key;
    },

    /** Формат времени HH:MM */
    formatTime(timeStr) {
        if (!timeStr) return '';
        return timeStr;
    },

    /** "14:00 — 15:30" */
    formatTimeRange(start, end) {
        if (!start && !end) return 'Весь день';
        if (!start) return `до ${end}`;
        if (!end) return `с ${start}`;
        return `${start} — ${end}`;
    },

    /** Relative time: "5 мин назад", "через 2 часа" */
    relativeTime(dateStr, timeStr) {
        const d = this.parseDate(dateStr);
        if (timeStr) {
            const [h, m] = timeStr.split(':').map(Number);
            d.setHours(h, m, 0, 0);
        }
        const now = new Date();
        const diffMs = d - now;
        const diffMin = Math.round(diffMs / 60000);

        if (diffMin < 0) {
            const absMin = Math.abs(diffMin);
            if (absMin < 60) return `${absMin} мин назад`;
            const hours = Math.floor(absMin / 60);
            if (hours < 24) return `${hours} ч назад`;
            return `${Math.floor(hours / 24)} дн назад`;
        } else {
            if (diffMin < 60) return `через ${diffMin} мин`;
            const hours = Math.floor(diffMin / 60);
            if (hours < 24) return `через ${hours} ч`;
            return `через ${Math.floor(hours / 24)} дн`;
        }
    },

    /** Debounce */
    debounce(fn, delay) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), delay);
        };
    },

    /** Экранирование HTML */
    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
};
