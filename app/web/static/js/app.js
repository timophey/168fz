// Глобальные переменные
let currentReport = null;
let reportFormat = 'table';

// Инициализация при загрузке страницы
function init() {
    loadDictionariesStatus();
    loadSyncStatus();
    loadSources();
    
    // Слушатель изменения формата отчета
    document.getElementById('reportFormat').addEventListener('change', function(e) {
        reportFormat = e.target.value;
    });
}

// Запуск инициализации - если DOM уже загружен, вызываем сразу,
// иначе ждем события DOMContentLoaded
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// ==================== API CALLS ====================

async function apiCall(endpoint, method = 'GET', body = null, isFormData = false) {
    const options = {
        method: method,
    };
    
    if (body && !isFormData) {
        options.headers = {
            'Content-Type': 'application/json',
        };
        options.body = JSON.stringify(body);
    } else if (body && isFormData) {
        options.body = body;
    }
    
    try {
        const response = await fetch(endpoint, options);
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Ошибка API');
        }
        
        return data.data;
    } catch (error) {
        console.error('API Error:', error);
        showAlert('Ошибка: ' + error.message, 'danger');
        throw error;
    }
}

// ==================== TEXT CHECKING ====================

async function checkText() {
    // Определяем активную панель
    const activeTab = document.querySelector('#inputTabs .nav-link.active');
    const tabId = activeTab.getAttribute('data-bs-target');
    
    const progress = document.getElementById('progress');
    const resultsDiv = document.getElementById('results');
    
    // Показываем прогресс
    progress.classList.remove('d-none');
    resultsDiv.classList.add('d-none');
    
    try {
        let data;
        
        if (tabId === '#text-panel') {
            // Проверка текста
            const text = document.getElementById('textInput').value.trim();
            if (!text) {
                showAlert('Введите текст для проверки', 'warning');
                progress.classList.add('d-none');
                return;
            }
            
            data = await apiCall('/api/v1/check', 'POST', { text });
            
        } else if (tabId === '#url-panel') {
            // Проверка по URL
            const url = document.getElementById('urlInput').value.trim();
            if (!url) {
                showAlert('Введите URL для проверки', 'warning');
                progress.classList.add('d-none');
                return;
            }
            
            // Добавляем протокол если отсутствует
            let fullUrl = url;
            if (!url.startsWith('http://') && !url.startsWith('https://')) {
                fullUrl = 'https://' + url;
            }
            
            data = await apiCall('/api/v1/check', 'POST', { url: fullUrl });
            
        } else if (tabId === '#file-panel') {
            // Проверка файла
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) {
                showAlert('Выберите файл для проверки', 'warning');
                progress.classList.add('d-none');
                return;
            }
            
            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);
            
            data = await apiCall('/api/v1/check/file', 'POST', formData, true);
        }
        
        currentReport = data;
        displayDetailedResults(data);
        
        progress.classList.add('d-none');
        resultsDiv.classList.remove('d-none');
        
    } catch (error) {
        progress.classList.add('d-none');
    }
}

function displayDetailedResults(data) {
    const container = document.getElementById('resultsContent');
    const stats = data.statistics;
    const checks = data.checks;
    const summary = data.summary;
    const allWords = data.all_words || [];
    const sourceInfo = data.source_info;
    
    // Статистика по статусам
    const statusCounts = {
        ok: 0,
        prohibited: 0,
        foreign: 0,
        normative_violation: 0
    };
    
    allWords.forEach(w => {
        if (statusCounts[w.status] !== undefined) {
            statusCounts[w.status]++;
        }
    });
    
    let html = '';
    
    // Информация об источнике
    if (sourceInfo) {
        html += '<div class="alert alert-info mb-3"><i class="fas fa-info-circle"></i> <strong>Источник:</strong> ';
        if (sourceInfo.type === 'url') {
            html += `URL: <a href="${escapeHtml(sourceInfo.url)}" target="_blank">${escapeHtml(sourceInfo.url)}</a><br>`;
            html += `Извлечено символов: ${sourceInfo.chars_extracted.toLocaleString()} | слов: ${sourceInfo.words_extracted.toLocaleString()}`;
        } else if (sourceInfo.type === 'file') {
            html += `Файл: ${escapeHtml(sourceInfo.filename)}<br>`;
            html += `Размер: ${(sourceInfo.file_size / 1024).toFixed(1)} KB | символов: ${sourceInfo.chars_extracted.toLocaleString()} | слов: ${sourceInfo.words_extracted.toLocaleString()}`;
        }
        html += '</div>';
    }
    
    // Основная статистика
    html += `
        <div class="row mb-3">
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h3>${stats.total_words.toLocaleString()}</h3>
                        <small class="text-muted">Всего слов</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h3>${stats.unique_words.toLocaleString()}</h3>
                        <small class="text-muted">Уникальных</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h3 class="risk-${summary.risk_level}">${getRiskLabel(summary.risk_level)}</h3>
                        <small class="text-muted">Уровень риска</small>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card bg-light">
                    <div class="card-body text-center">
                        <h3>${summary.violation_count}</h3>
                        <small class="text-muted">Нарушений</small>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Детальная статистика по статусам
    html += `
        <div class="card mb-3">
            <div class="card-header bg-light">
                <h6 class="mb-0"><i class="fas fa-chart-pie"></i> Статистика по статусам слов</h6>
            </div>
            <div class="card-body">
                <div class="row text-center">
                    <div class="col-md-3">
                        <span class="badge bg-success fs-6">✅ Нормальные: ${statusCounts.ok.toLocaleString()}</span>
                    </div>
                    <div class="col-md-3">
                        <span class="badge bg-danger fs-6">⛔ Запрещенные: ${statusCounts.prohibited.toLocaleString()}</span>
                    </div>
                    <div class="col-md-3">
                        <span class="badge bg-warning text-dark fs-6">🌐 Иностранные: ${statusCounts.foreign.toLocaleString()}</span>
                    </div>
                    <div class="col-md-3">
                        <span class="badge bg-info text-dark fs-6">📚 Нарушения: ${statusCounts.normative_violation.toLocaleString()}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Таблица всех слов
    if (allWords.length > 0) {
        html += `
            <div class="card mb-3">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                    <h6 class="mb-0"><i class="fas fa-list"></i> Все слова текста (${allWords.length})</h6>
                    <div>
                        <input type="text" class="form-control form-control-sm" id="wordFilter"
                               placeholder="Фильтр слов..." style="width: 200px; display: inline-block;">
                    </div>
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive" style="max-height: 500px; overflow-y: auto;">
                        <table class="table table-sm table-hover mb-0" id="wordsTable">
                            <thead class="table-light sticky-top">
                                <tr>
                                    <th style="width: 5%; cursor: pointer;" onclick="sortTable('num')"># <i class="sort-icon fas fa-sort" data-sort="num"></i></th>
                                    <th style="width: 20%; cursor: pointer;" onclick="sortTable('word')">Слово <i class="sort-icon fas fa-sort" data-sort="word"></i></th>
                                    <th style="width: 10%; cursor: pointer;" onclick="sortTable('count')">Кол-во <i class="sort-icon fas fa-sort" data-sort="count"></i></th>
                                    <th style="width: 15%; cursor: pointer;" onclick="sortTable('status')">Статус <i class="sort-icon fas fa-sort" data-sort="status"></i></th>
                                    <th style="width: 25%;">Категории</th>
                                    <th style="width: 25%;">Рекомендация / Статья</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        allWords.forEach((wordData, index) => {
            const statusBadge = getStatusBadge(wordData.status);
            const statusTitle = getStatusTitle(wordData.status);
            const rowClass = getStatusRowClass(wordData.status);
            const count = wordData.count || 1;
            
            let categoriesHtml = wordData.categories.map(cat =>
                `<span class="badge bg-secondary">${escapeHtml(cat)}</span>`
            ).join(' ');
            
            let recommendationHtml = '';
            if (wordData.law_article) {
                recommendationHtml = `<span class="text-danger small">${escapeHtml(wordData.law_article)}</span>`;
            } else if (wordData.recommendation) {
                recommendationHtml = `<span class="text-warning small">${escapeHtml(wordData.recommendation)}</span>`;
            } else if (wordData.status === 'ok') {
                recommendationHtml = '<span class="text-success small">✅ Соответствует нормам</span>';
            }
            
            html += `
                <tr class="${rowClass}" data-word="${escapeHtml(wordData.word.toLowerCase())}" data-count="${count}" data-status="${wordData.status}">
                    <td class="sort-num">${index + 1}</td>
                    <td class="sort-word"><strong>${escapeHtml(wordData.word)}</strong></td>
                    <td class="sort-count">${count}</td>
                    <td class="sort-status">${statusBadge} <small class="text-muted">${statusTitle}</small></td>
                    <td>${categoriesHtml}</td>
                    <td>${recommendationHtml}</td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div></div>`;
        
        // Легенда статусов
        html += `
            <div class="card-footer bg-light">
                <small>
                    <strong>Легенда:</strong><br>
                    <span class="badge bg-success">OK</span> - слово соответствует нормам<br>
                    <span class="badge bg-danger">Запрещено</span> - ненормативная лексика (ст. 6.1)<br>
                    <span class="badge bg-warning text-dark">Иностранное</span> - рекомендуется заменить<br>
                    <span class="badge bg-info text-dark">Нарушение</span> - некорректное употребление
                </small>
            </div>
        `;
    }
    
    // Запрещенные слова (отдельный блок)
    if (checks.prohibited_words && checks.prohibited_words.length > 0) {
        html += `
            <div class="card border-danger mb-3">
                <div class="card-header bg-danger text-white">
                    <i class="fas fa-exclamation-triangle"></i> Запрещенные слова (${checks.prohibited_words.length})
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Слово</th>
                                    <th>Кол-во</th>
                                    <th>Статья закона</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        checks.prohibited_words.forEach(item => {
            html += `
                <tr class="table-danger">
                    <td><strong>${escapeHtml(item.word)}</strong></td>
                    <td>${item.count}</td>
                    <td>${escapeHtml(item.law_article || '-')}</td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div></div></div>`;
    }
    
    // Иностранные слова
    if (checks.foreign_words && checks.foreign_words.length > 0) {
        html += `
            <div class="card border-warning mb-3">
                <div class="card-header bg-warning text-dark">
                    <i class="fas fa-language"></i> Иностранные слова (${checks.foreign_words.length})
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Слово</th>
                                    <th>Кол-во</th>
                                    <th>Рекомендация</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        checks.foreign_words.forEach(item => {
            html += `
                <tr class="table-warning">
                    <td>${escapeHtml(item.word)}</td>
                    <td>${item.count}</td>
                    <td>${escapeHtml(item.recommendation || '-')}</td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div></div></div>`;
    }
    
    // Нарушения норм
    if (checks.normative_violations && checks.normative_violations.length > 0) {
        html += `
            <div class="card border-info mb-3">
                <div class="card-header bg-info text-white">
                    <i class="fas fa-book-open"></i> Нарушения норм (${checks.normative_violations.length})
                </div>
                <div class="card-body p-0">
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead>
                                <tr>
                                    <th>Слово</th>
                                    <th>Кол-во</th>
                                    <th>Проблема</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        checks.normative_violations.forEach(item => {
            html += `
                <tr class="table-info">
                    <td>${escapeHtml(item.word)}</td>
                    <td>${item.count}</td>
                    <td>${escapeHtml(item.issue || '-')}</td>
                </tr>
            `;
        });
        
        html += `</tbody></table></div></div></div>`;
    }
    
    // Рекомендации
    if (checks.recommendations && checks.recommendations.length > 0) {
        html += `
            <div class="card mb-3">
                <div class="card-header bg-light">
                    <i class="fas fa-lightbulb text-warning"></i> Рекомендации
                </div>
                <div class="card-body">
                    <ul class="list-unstyled mb-0">
        `;
        
        checks.recommendations.forEach(rec => {
            html += `<li class="mb-2">${escapeHtml(rec)}</li>`;
        });
        
        html += `</ul></div></div>`;
    }
    
    container.innerHTML = html;
    
    // Добавляем фильтрацию слов
    setTimeout(() => {
        const filterInput = document.getElementById('wordFilter');
        if (filterInput) {
            filterInput.addEventListener('input', function() {
                filterWordsTable(this.value.toLowerCase());
            });
        }
    }, 100);
}

function getStatusBadge(status) {
    const badges = {
        'ok': '<span class="badge bg-success">OK</span>',
        'prohibited': '<span class="badge bg-danger">Запрещено</span>',
        'foreign': '<span class="badge bg-warning text-dark">Иностранное</span>',
        'normative_violation': '<span class="badge bg-info text-dark">Нарушение</span>'
    };
    return badges[status] || '<span class="badge bg-secondary">Неизвестно</span>';
}

function getStatusTitle(status) {
    const titles = {
        'ok': 'Соответствует нормам',
        'prohibited': 'Запрещенное слово',
        'foreign': 'Иностранное слово',
        'normative_violation': 'Нарушение нормы'
    };
    return titles[status] || status;
}

function getStatusRowClass(status) {
    const classes = {
        'ok': '',
        'prohibited': 'table-danger',
        'foreign': 'table-warning',
        'normative_violation': 'table-info'
    };
    return classes[status] || '';
}

// Глобальные переменные для сортировки
let currentSort = {
    column: 'count',  // По умолчанию сортируем по кол-ву (самые частые сверху)
    direction: 'desc'
};

function sortTable(column) {
    const table = document.getElementById('wordsTable');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Определяем направление сортировки
    if (currentSort.column === column) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = column === 'word' || column === 'status' ? 'asc' : 'desc';
    }
    
    // Сортируем строки
    rows.sort((a, b) => {
        let aVal, bVal;
        
        switch (column) {
            case 'num':
                aVal = parseInt(a.querySelector('.sort-num').textContent);
                bVal = parseInt(b.querySelector('.sort-num').textContent);
                break;
            case 'word':
                aVal = a.querySelector('.sort-word').textContent.toLowerCase();
                bVal = b.querySelector('.sort-word').textContent.toLowerCase();
                break;
            case 'count':
                aVal = parseInt(a.getAttribute('data-count'));
                bVal = parseInt(b.getAttribute('data-count'));
                break;
            case 'status':
                aVal = a.getAttribute('data-status');
                bVal = b.getAttribute('data-status');
                break;
            default:
                return 0;
        }
        
        if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });
    
    // Обновляем порядок строк в таблице
    rows.forEach(row => tbody.appendChild(row));
    
    // Обновляем иконки сортировки
    updateSortIcons();
    
    // Пересчитываем номера строк
    updateRowNumbers();
}

function updateSortIcons() {
    // Сбрасываем все иконки
    document.querySelectorAll('.sort-icon').forEach(icon => {
        icon.className = 'sort-icon fas fa-sort';
    });
    
    // Устанавливаем активную иконку
    const activeIcon = document.querySelector(`.sort-icon[data-sort="${currentSort.column}"]`);
    if (activeIcon) {
        activeIcon.className = `sort-icon fas fa-sort-${currentSort.direction === 'asc' ? 'up' : 'down'}`;
    }
}

function updateRowNumbers() {
    const rows = document.querySelectorAll('#wordsTable tbody tr');
    rows.forEach((row, index) => {
        row.querySelector('.sort-num').textContent = index + 1;
    });
}

function filterWordsTable(filter) {
    const table = document.getElementById('wordsTable');
    if (!table) return;
    
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const word = row.getAttribute('data-word');
        const text = row.textContent.toLowerCase();
        if (word.includes(filter) || text.includes(filter)) {
            row.style.display = '';
        } else {
            row.style.display = 'none';
        }
    });
}

function getRiskLabel(level) {
    const labels = {
        'low': '🟢 Низкий',
        'medium': '🟡 Средний',
        'high': '🔴 Высокий'
    };
    return labels[level] || level;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showAlert(message, type = 'info') {
    // Удаляем существующие алерты
    const existingAlert = document.querySelector('.alert-auto-dismiss');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-auto-dismiss alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container-fluid').insertBefore(alert, document.querySelector('.row'));
    
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// ==================== DOWNLOAD REPORT ====================

function downloadReport() {
    if (!currentReport) {
        showAlert('Сначала выполните проверку текста', 'warning');
        return;
    }
    
    const format = document.getElementById('reportFormat').value;
    let content, filename, mimeType;
    
    if (format === 'json') {
        content = JSON.stringify(currentReport, null, 2);
        filename = 'report.json';
        mimeType = 'application/json';
    } else {
        // Генерируем текстовый отчет (упрощенный)
        content = generateTextReport(currentReport);
        filename = 'report.txt';
        mimeType = 'text/plain';
    }
    
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function generateTextReport(data) {
    let report = 'ОТЧЕТ О ПРОВЕРКЕ ТЕКСТА НА СООТВЕТСТВИЕ ЗАКОНУ № 168-ФЗ\n';
    report += '='.repeat(60) + '\n\n';
    
    // Информация об источнике
    if (data.source_info) {
        report += 'ИСТОЧНИК:\n';
        const src = data.source_info;
        if (src.type === 'url') {
            report += `  Тип: URL\n  Адрес: ${src.url}\n`;
        } else if (src.type === 'file') {
            report += `  Тип: Файл\n  Имя: ${src.filename}\n  Размер: ${(src.file_size/1024).toFixed(1)} KB\n`;
        }
        report += `  Символов извлечено: ${src.chars_extracted}\n  Слов: ${src.words_extracted}\n\n`;
    }
    
    report += 'СТАТИСТИКА:\n';
    report += `  Всего символов: ${data.statistics.total_chars}\n`;
    report += `  Всего слов: ${data.statistics.total_words}\n`;
    report += `  Уникальных слов: ${data.statistics.unique_words}\n\n`;
    
    if (data.checks.prohibited_words && data.checks.prohibited_words.length > 0) {
        report += 'ЗАПРЕЩЕННЫЕ СЛОВА:\n';
        data.checks.prohibited_words.forEach(item => {
            report += `  ${item.word} (x${item.count}) - ${item.law_article || 'Не указана'}\n`;
        });
        report += '\n';
    }
    
    if (data.checks.foreign_words && data.checks.foreign_words.length > 0) {
        report += 'ИНОСТРАННЫЕ СЛОВА:\n';
        data.checks.foreign_words.forEach(item => {
            report += `  ${item.word} (x${item.count}) - ${item.recommendation || 'Нет рекомендации'}\n`;
        });
        report += '\n';
    }
    
    report += 'РЕКОМЕНДАЦИИ:\n';
    data.checks.recommendations.forEach(rec => {
        report += `  - ${rec}\n`;
    });
    report += '\n';
    
    report += `УРОВЕНЬ РИСКА: ${getRiskLabel(data.summary.risk_level)}\n`;
    report += `НАРУШЕНИЙ: ${data.summary.violation_count}\n`;
    
    return report;
}

// ==================== DICTIONARIES ====================

async function loadDictionariesStatus() {
    try {
        const dictionaries = await apiCall('/api/v1/dictionaries');
        const container = document.getElementById('dictionariesStatus');
        
        if (dictionaries.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">Словари не загружены</div>';
            return;
        }
        
        let html = '<div class="row">';
        dictionaries.forEach(dict => {
            html += `
                <div class="col-md-6">
                    <div class="dict-item synced">
                        <div class="dict-name">${escapeHtml(dict.name)}</div>
                        <div class="dict-meta">
                            ${dict.words_count.toLocaleString()} слов | версия ${dict.version || 'N/A'}
                        </div>
                    </div>
                </div>
            `;
        });
        html += '</div>';
        
        container.innerHTML = html;
    } catch (error) {
        document.getElementById('dictionariesStatus').innerHTML = 
            '<div class="alert alert-danger">Ошибка загрузки словарей</div>';
    }
}

// ==================== SYNC ====================

async function loadSyncStatus() {
    try {
        const status = await apiCall('/api/v1/sync/status');
        const container = document.getElementById('syncStatus');
        
        let html = '';
        if (status.dictionaries) {
            Object.entries(status.dictionaries).forEach(([name, info]) => {
                const isSynced = info.synced;
                const icon = isSynced ? '✓' : '✗';
                const textClass = isSynced ? 'success' : 'error';
                
                html += `
                    <div class="sync-item ${textClass}">
                        <strong>${icon} ${name}</strong>
                        ${isSynced ? `(${info.word_count ? info.word_count.toLocaleString() : 0} слов)` : ''}
                    </div>
                `;
            });
        }
        
        html += `<div class="mt-2 text-muted small">
            Последняя синхронизация: ${status.last_full_sync ? new Date(status.last_full_sync).toLocaleString() : 'Никогда'}
        </div>`;
        
        container.innerHTML = html;
    } catch (error) {
        document.getElementById('syncStatus').innerHTML = 
            '<div class="alert alert-danger">Ошибка загрузки статуса</div>';
    }
}

async function syncAll() {
    if (!confirm('Синхронизировать все словари? Это может занять некоторое время.')) {
        return;
    }
    
    try {
        showAlert('Синхронизация начата...', 'info');
        const result = await apiCall('/api/v1/sync/all', 'POST');
        showAlert(result.message, 'success');
        loadSyncStatus();
        loadDictionariesStatus();
    } catch (error) {
        // Ошибка уже показана в apiCall
    }
}

// ==================== SOURCES ====================

async function loadSources() {
    try {
        const sources = await apiCall('/api/v1/sources');
        const container = document.getElementById('sourcesList');
        
        let html = '';
        if (sources.real && sources.real.length > 0) {
            html += '<h6>Доступные источники:</h6>';
            sources.real.forEach(source => {
                html += `
                    <div class="source-item">
                        <div class="source-name">${escapeHtml(source.official_name)}</div>
                        <div class="source-institution">${escapeHtml(source.institution)}</div>
                    </div>
                `;
            });
        }
        
        if (sources.legacy && sources.legacy.length > 0) {
            html += '<h6 class="mt-3">Legacy источники:</h6>';
            sources.legacy.forEach(source => {
                html += `
                    <div class="source-item" style="border-left-color: #6c757d;">
                        <div class="source-name">${escapeHtml(source.official_name)}</div>
                        <div class="source-institution">${escapeHtml(source.institution)}</div>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html || '<div class="alert alert-info">Нет доступных источников</div>';
    } catch (error) {
        document.getElementById('sourcesList').innerHTML = 
            '<div class="alert alert-danger">Ошибка загрузки источников</div>';
    }
}

// ==================== UPLOAD DICTIONARY ====================

async function uploadDictionary() {
    const fileInput = document.getElementById('dictFile');
    const nameInput = document.getElementById('dictName');
    
    if (!fileInput.files.length) {
        showAlert('Выберите файл словаря', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', nameInput.value || file.name);
    
    // Для простоты - отправляем путь к файлу (в реальности нужно загружать файл)
    // В данном случае просто показываем сообщение
    showAlert('Загрузка файлов через веб-интерфейс требует дополнительной настройки. Используйте API или CLI.', 'info');
    
    // TODO: Реализовать загрузку файла через /api/v1/dictionaries/load
}

// ==================== UTILS ====================

function clearInput() {
    // Очищаем все поля ввода
    document.getElementById('textInput').value = '';
    document.getElementById('urlInput').value = '';
    document.getElementById('fileInput').value = '';
    document.getElementById('results').classList.add('d-none');
    currentReport = null;
}

// Экспорт функций в глобальную область
window.checkText = checkText;
window.clearText = clearInput;
window.downloadReport = downloadReport;
window.syncAll = syncAll;
window.loadSyncStatus = loadSyncStatus;
window.uploadDictionary = uploadDictionary;
