// Глобальные переменные
let adminKey = ''; // Админ-ключ для API запросов

// Инициализация при загрузке страницы
function init() {
    // Проверяем, есть ли уже сохраненный ключ в сессии
    const savedKey = getAdminKey();
    if (savedKey) {
        // Пробуем автоматически войти
        verifyKey(savedKey).then(isValid => {
            if (isValid) {
                showAdminContent();
            } else {
                // Ключ невалиден, очищаем и показываем форму
                clearAdminKey();
                showLoginForm();
            }
        });
    } else {
        // Нет ключа, показываем форму входа
        showLoginForm();
    }
    
    // Обработчик формы авторизации
    document.getElementById('authForm').addEventListener('submit', handleLogin);
}

// Показ формы входа
function showLoginForm() {
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('adminContent').classList.remove('authenticated');
    document.getElementById('adminKeyInput').focus();
}

// Показ админ-контента
function showAdminContent() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('adminContent').classList.add('authenticated');
    
    // Загружаем данные
    loadSyncStatus();
    loadSources();
    loadAllDictionariesStatus();
    loadUserDictionaries();
}

// Обработка входа
async function handleLogin(e) {
    e.preventDefault();
    const key = document.getElementById('adminKeyInput').value.trim();
    const errorDiv = document.getElementById('authError');
    
    if (!key) {
        errorDiv.textContent = 'Введите админ-ключ';
        errorDiv.classList.remove('d-none');
        return;
    }
    
    // Проверяем ключ
    const isValid = await verifyKey(key);
    if (isValid) {
        setAdminKey(key);
        showAdminContent();
        errorDiv.classList.add('d-none');
    } else {
        errorDiv.textContent = 'Неверный админ-ключ. Попробуйте снова.';
        errorDiv.classList.remove('d-none');
        document.getElementById('adminKeyInput').value = '';
        document.getElementById('adminKeyInput').focus();
    }
}

// Проверка ключа через тестовый API запрос
async function verifyKey(key) {
    try {
        // Пробуем сделать запрос, который требует админ-прав
        const response = await fetch('/api/v1/sync/status?' + new URLSearchParams({ admin_key: key }));
        if (response.ok) {
            return true;
        }
        const data = await response.json();
        if (data.detail && data.detail.includes('Неверный админ-ключ')) {
            return false;
        }
        // Если другой ответ, считаем что ключ валиден (например, если endpoint вернул данные)
        return response.status === 200;
    } catch (error) {
        console.error('Key verification error:', error);
        return false;
    }
}

// Выход
function logout() {
    clearAdminKey();
    document.getElementById('authForm').reset();
    document.getElementById('authError').classList.add('d-none');
    showLoginForm();
}

// ==================== AUTHENTICATION ====================

function getAdminKey() {
    // Сначала проверяем sessionStorage (сессия браузера)
    let key = sessionStorage.getItem('admin_key');
    if (!key) {
        // Если нет в sessionStorage, проверяем localStorage (для запоминания между сессиями)
        key = localStorage.getItem('admin_key');
    }
    return key || '';
}

function setAdminKey(key) {
    sessionStorage.setItem('admin_key', key);
    // Не сохраняем в localStorage по соображениям безопасности
    adminKey = key;
}

function clearAdminKey() {
    sessionStorage.removeItem('admin_key');
    localStorage.removeItem('admin_key');
    adminKey = '';
}

// ==================== API CALLS ====================

async function apiCall(endpoint, method = 'GET', body = null, isFormData = false) {
    const options = {
        method: method,
        headers: {}
    };
    
    // Всегда добавляем админ-ключ (должен быть установлен после успешной авторизации)
    const key = getAdminKey();
    if (key) {
        options.headers['X-Admin-Key'] = key;
    } else {
        // Если ключ не установлен, показываем ошибку и перенаправляем на логин
        showAlert('Требуется авторизация. Перенаправление на страницу входа...', 'warning');
        setTimeout(() => {
            showLoginForm();
        }, 1000);
        throw new Error('Не авторизован');
    }
    
    if (body && !isFormData) {
        options.headers['Content-Type'] = 'application/json';
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
        // Если ошибка аутентификации, предлагаем ввести ключ заново
        if (error.message.includes('Требуется аутентификация') || error.message.includes('Неверный админ-ключ')) {
            alert('Ошибка аутентификации. Введите корректный админ-ключ.');
            clearAdminKey();
            window.location.reload();
            return;
        }
        showAlert('Ошибка: ' + error.message, 'danger');
        throw error;
    }
}

// ==================== SYNC ====================

async function loadSyncStatus() {
    try {
        // Получаем и статус синхронизации, и список загруженных словарей
        const [status, dictionaries] = await Promise.all([
            apiCall('/api/v1/sync/status'),
            apiCall('/api/v1/dictionaries')
        ]);
        
        const container = document.getElementById('syncStatus');
        const loadedDicts = new Set(dictionaries.map(d => d.name));
        
        let html = '';
        if (status.dictionaries) {
            html += '<div class="table-responsive"><table class="table table-sm table-hover mb-0">';
            html += `
                <thead>
                    <tr>
                        <th>Категория</th>
                        <th>Словарь</th>
                        <th>Слов</th>
                        <th>Статус</th>
                        <th>Действия</th>
                    </tr>
                </thead>
                <tbody>
            `;
            
            Object.entries(status.dictionaries).forEach(([name, info]) => {
                const isSynced = info.synced;
                const isLoaded = loadedDicts.has(name);
                const category = isLoaded ? (dictionaries.find(d => d.name === name)?.category || 'Другие словари') : '—';
                const color = isLoaded ? getCategoryColor(category) : 'secondary';
                const categoryBadge = isLoaded ?
                    `<span class="badge bg-${color}">${escapeHtml(category)}</span>` :
                    '—';
                
                const statusBadge = isSynced ?
                    '<span class="badge bg-success">Актуален</span>' :
                    '<span class="badge bg-warning text-dark">Требует обновления</span>';
                
                const wordCount = isSynced ? (info.word_count ? info.word_count.toLocaleString() : 'N/A') : '—';
                const lastSync = info.last_sync ? new Date(info.last_sync).toLocaleDateString() : '—';
                
                html += `
                    <tr>
                        <td>${categoryBadge}</td>
                        <td><strong>${escapeHtml(info.official_name || name)}</strong><br><small class="text-muted">${escapeHtml(name)}</small></td>
                        <td>${wordCount}</td>
                        <td>${statusBadge}<br><small class="text-muted">${isSynced ? lastSync : 'Не синхронизирован'}</small></td>
                        <td>
                            ${isLoaded ? `
                                <button class="btn btn-sm btn-outline-primary" onclick="exportDictionary('${name}')" title="Экспорт в XLSX">
                                    <i class="fas fa-download"></i> XLSX
                                </button>
                            ` : '<span class="text-muted small">Не загружен</span>'}
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table></div>';
        }
        
        const lastFullSync = status.last_full_sync ? new Date(status.last_full_sync).toLocaleString() : 'Никогда';
        html += `<div class="mt-3 border-top pt-2">
            <strong>Последняя полная синхронизация:</strong> ${lastFullSync}
        </div>`;
        
        container.innerHTML = html || '<div class="alert alert-info">Нет данных о синхронизации</div>';
    } catch (error) {
        document.getElementById('syncStatus').innerHTML =
            '<div class="alert alert-danger">Ошибка загрузки статуса синхронизации</div>';
    }
}

async function syncAll() {
    if (!confirm('Синхронизировать все официальные словари? Это может занять некоторое время.')) {
        return;
    }
    
    try {
        showAlert('Синхронизация начата...', 'info');
        const result = await apiCall('/api/v1/sync/all', 'POST');
        showAlert(result.message, 'success');
        
        // Обновляем все статусы
        setTimeout(() => {
            loadSyncStatus();
            loadAllDictionariesStatus();
            loadUserDictionaries();
        }, 1000);
    } catch (error) {
        // Ошибка уже показана в apiCall
    }
}

// ==================== DICTIONARIES MANAGEMENT ====================

async function loadAllDictionariesStatus() {
    try {
        const dictionaries = await apiCall('/api/v1/dictionaries');
        const container = document.getElementById('allDictionariesStatus');
        
        if (dictionaries.length === 0) {
            container.innerHTML = '<div class="alert alert-warning">Словари не загружены</div>';
            return;
        }
        
        // Get unique categories for filter
        const categories = [...new Set(dictionaries.map(d => d.category || 'Другие словари'))];
        const filterSelect = document.getElementById('categoryFilter');
        if (filterSelect) {
            filterSelect.innerHTML = '<option value="">Все категории</option>';
            categories.sort().forEach(cat => {
                filterSelect.innerHTML += `
                    <option value="${escapeHtml(cat)}">${escapeHtml(cat)}</option>
                `;
            });
        }
        
        let html = '<div class="table-responsive"><table class="table table-sm table-hover mb-0" id="allDictsTable">';
        html += `
            <thead>
                <tr>
                    <th>Категория</th>
                    <th>Словарь</th>
                    <th>Тип</th>
                    <th>Слов</th>
                    <th>Версия</th>
                    <th>Статус</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        dictionaries.forEach(dict => {
            const statusBadge = dict.synced ? 
                '<span class="badge bg-success">Актуален</span>' : 
                '<span class="badge bg-warning text-dark">Требует обновления</span>';
            
            const category = dict.category || 'Другие словари';
            const color = getCategoryColor(category);
            const categoryBadge = `<span class="badge bg-${color} category-badge">${escapeHtml(category)}</span>`;
            
            html += `
                <tr data-category="${escapeHtml(category)}">
                    <td>${categoryBadge}</td>
                    <td><strong>${escapeHtml(dict.name)}</strong></td>
                    <td>${escapeHtml(dict.source || 'unknown')}</td>
                    <td>${dict.words_count ? dict.words_count.toLocaleString() : 'N/A'}</td>
                    <td>${escapeHtml(dict.version || 'N/A')}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
        
        // Add filter functionality
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', function() {
                const selectedCategory = this.value;
                const rows = container.querySelectorAll('#allDictsTable tbody tr');
                rows.forEach(row => {
                    if (selectedCategory === '' || row.dataset.category === selectedCategory) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        }
    } catch (error) {
        document.getElementById('allDictionariesStatus').innerHTML = 
            '<div class="alert alert-danger">Ошибка загрузки списка словарей</div>';
    }
}

async function loadUserDictionaries() {
    try {
        const allDicts = await apiCall('/api/v1/dictionaries');
        const userDicts = allDicts.filter(d => d.source === 'user' || d.name.startsWith('user_'));
        const container = document.getElementById('userDictionariesList');
        
        if (userDicts.length === 0) {
            container.innerHTML = '<div class="alert alert-info">Пользовательские словари не загружены</div>';
            return;
        }
        
        let html = '<div class="table-responsive"><table class="table table-sm table-hover mb-0" id="userDictsTable">';
        html += `
            <thead>
                <tr>
                    <th>Категория</th>
                    <th>Имя</th>
                    <th>Слов</th>
                    <th>Версия</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        userDicts.forEach(dict => {
            const category = dict.category || 'Другие словари';
            const color = getCategoryColor(category);
            const categoryBadge = `<span class="badge bg-${color} category-badge">${escapeHtml(category)}</span>`;
            
            html += `
                <tr data-category="${escapeHtml(category)}">
                    <td>${categoryBadge}</td>
                    <td><strong>${escapeHtml(dict.name)}</strong></td>
                    <td>${dict.words_count ? dict.words_count.toLocaleString() : 'N/A'}</td>
                    <td>${escapeHtml(dict.version || 'N/A')}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="exportDictionary('${dict.name}')" title="Экспорт в XLSX">
                            <i class="fas fa-download"></i> XLSX
                        </button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteDictionary('${dict.name}')" title="Удалить">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
        
        // Add filter functionality (shared with all dictionaries table)
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            // Сохраняем текущий фильтр и применяем к новой таблице
            const currentFilter = categoryFilter.value;
            categoryFilter.dispatchEvent(new Event('change'));
        }
    } catch (error) {
        document.getElementById('userDictionariesList').innerHTML = 
            '<div class="alert alert-danger">Ошибка загрузки пользовательских словарей</div>';
    }
}

async function uploadDictionary() {
    const fileInput = document.getElementById('dictFile');
    const nameInput = document.getElementById('dictName');
    
    if (!fileInput.files.length) {
        showAlert('Выберите файл словаря', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    
    if (!confirm(`Загрузить словарь из файла "${file.name}"?`)) {
        return;
    }
    
    try {
        showAlert('Загрузка словаря...', 'info');
        
        // Читаем файл и отправляем его содержимое
        const text = await file.text();
        let dictData;
        
        try {
            dictData = JSON.parse(text);
        } catch (e) {
            // Если не JSON, обрабатываем как CSV или TXT
            const lines = text.split('\n').filter(line => line.trim());
            dictData = { words: lines };
        }
        
        // Создаем временный файл на сервере через API
        // Пока что используем упрощенный подход - передаем данные напрямую
        // В реальности нужно загружать файл, но для простоты будем передавать содержимое
        
        // TODO: Реализовать полноценную загрузку файла через multipart/form-data
        showAlert('Загрузка файлов через веб-интерфейс в разработке. Используйте CLI или API напрямую.', 'info');
        
    } catch (error) {
        showAlert('Ошибка загрузки словаря: ' + error.message, 'danger');
    }
}

async function deleteDictionary(dictName) {
    if (!confirm(`Удалить словарь "${dictName}"? Это действие нельзя отменить.`)) {
        return;
    }
    
    try {
        showAlert(`Удаление словаря "${dictName}"...`, 'info');
        
        // Удаление через API - нужно добавить endpoint в main.py
        // Пока что показываем сообщение
        showAlert('Функция удаления словарей в разработке. Удалите файл вручную из папки dictionaries/data/', 'info');
        
        // TODO: Добавить DELETE /api/v1/dictionaries/{dict_name} endpoint
    } catch (error) {
        showAlert('Ошибка удаления словаря: ' + error.message, 'danger');
    }
}

// ==================== SOURCES ====================

async function loadSources() {
    try {
        const sources = await apiCall('/api/v1/sources');
        const container = document.getElementById('sourcesList');
        
        let html = '';
        if (sources.real && sources.real.length > 0) {
            html += '<h6>Официальные источники:</h6>';
            sources.real.forEach(source => {
                html += `
                    <div class="source-item border-start border-3 border-info ps-2 mb-2">
                        <div class="source-name fw-bold">${escapeHtml(source.official_name)}</div>
                        <div class="source-institution text-muted small">${escapeHtml(source.institution)}</div>
                        <div class="source-url small">
                            <a href="${escapeHtml(source.url)}" target="_blank" class="text-decoration-none">
                                <i class="fas fa-external-link-alt"></i> ${escapeHtml(source.url)}
                            </a>
                        </div>
                    </div>
                `;
            });
        }
        
        if (sources.legacy && sources.legacy.length > 0) {
            html += '<h6 class="mt-3">Legacy источники:</h6>';
            sources.legacy.forEach(source => {
                html += `
                    <div class="source-item border-start border-3 border-secondary ps-2 mb-2">
                        <div class="source-name fw-bold">${escapeHtml(source.official_name)}</div>
                        <div class="source-institution text-muted small">${escapeHtml(source.institution)}</div>
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

// ==================== USER DICTIONARIES ====================

async function downloadTemplate() {
    try {
        const response = await fetch('/api/v1/dictionaries/template/xlsx', {
            method: 'GET',
            headers: {
                'X-Admin-Key': getAdminKey()
            }
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Ошибка загрузки шаблона');
        }
        
        // Получаем blob и скачиваем
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'template_dictionary.xlsx';
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showAlert('Шаблон скачан', 'success');
    } catch (error) {
        showAlert('Ошибка скачивания шаблона: ' + error.message, 'danger');
    }
}

async function exportDictionary(dictName) {
    try {
        showAlert(`Экспорт словаря "${dictName}"...`, 'info');
        
        const response = await fetch(`/api/v1/dictionaries/${encodeURIComponent(dictName)}/export`, {
            method: 'GET',
            headers: {
                'X-Admin-Key': getAdminKey()
            }
        });
        
        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.detail || 'Ошибка экспорта');
        }
        
        // Получаем blob и скачиваем
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${dictName}.xlsx`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        showAlert(`Словарь "${dictName}" экспортирован`, 'success');
    } catch (error) {
        showAlert('Ошибка экспорта: ' + error.message, 'danger');
    }
}

async function uploadDictionary() {
    const fileInput = document.getElementById('dictFile');
    const nameInput = document.getElementById('dictName');
    const categorySelect = document.getElementById('dictCategory');
    const descInput = document.getElementById('dictDescription');
    const overwriteCheck = document.getElementById('dictOverwrite');
    
    if (!fileInput.files.length) {
        showAlert('Выберите файл словаря', 'warning');
        return;
    }
    
    const file = fileInput.files[0];
    const name = nameInput.value.trim() || null;
    const category = categorySelect.value.trim() || null;
    const description = descInput.value.trim() || null;
    const overwrite = overwriteCheck.checked;
    
    if (!confirm(`Импортировать словарь из файла "${file.name}"?${name ? `\nИмя: ${name}` : ''}${category ? `\nКатегория: ${category}` : ''}`)) {
        return;
    }
    
    try {
        showAlert('Импорт словаря...', 'info');
        
        // Подготавливаем FormData
        const formData = new FormData();
        formData.append('file', file);
        if (name) formData.append('name', name);
        if (category) formData.append('category', category);
        if (description) formData.append('description', description);
        formData.append('overwrite', overwrite);
        
        const response = await fetch('/api/v1/dictionaries/import', {
            method: 'POST',
            headers: {
                'X-Admin-Key': getAdminKey()
                // Не устанавливаем Content-Type - браузер установит multipart/form-data с boundary
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Ошибка импорта');
        }
        
        showAlert(`Словарь импортирован: ${data.data.name}`, 'success');
        
        // Очищаем форму
        fileInput.value = '';
        nameInput.value = '';
        categorySelect.value = '';
        descInput.value = '';
        overwriteCheck.checked = false;
        
        // Обновляем списки
        setTimeout(() => {
            loadUserDictionaries();
            loadAllDictionariesStatus();
        }, 500);
    } catch (error) {
        showAlert('Ошибка импорта: ' + error.message, 'danger');
    }
}

async function deleteDictionary(dictName) {
    if (!confirm(`Удалить словарь "${dictName}"? Это действие нельзя отменить.`)) {
        return;
    }
    
    try {
        showAlert(`Удаление словаря "${dictName}"...`, 'info');
        
        const response = await fetch(`/api/v1/dictionaries/${encodeURIComponent(dictName)}`, {
            method: 'DELETE',
            headers: {
                'X-Admin-Key': getAdminKey()
            }
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.detail || data.message || 'Ошибка удаления');
        }
        
        showAlert(`Словарь удален: ${dictName}`, 'success');
        
        // Обновляем списки
        setTimeout(() => {
            loadUserDictionaries();
            loadAllDictionariesStatus();
        }, 500);
    } catch (error) {
        showAlert('Ошибка удаления: ' + error.message, 'danger');
    }
}

// ==================== UTILS ====================

function getCategoryColor(category) {
    const colors = {
        'Запрещенные слова': 'danger',
        'Иностранные слова': 'primary',
        'Разрешенные иностранные термины': 'success',
        'Нормативные слова': 'info',
        'Термины': 'secondary',
        'Аббревиатуры': 'dark',
        'Топонимы': 'warning',
        'Профессионализмы и жаргон': 'warning',
        'Другие словари': 'light'
    };
    return colors[category] || 'secondary';
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
    alert.className = `alert alert-${type} alert-auto-dismiss alert-dismissible fade show mt-2`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Вставляем в начало контейнера или body
    const container = document.querySelector('.container-fluid');
    if (container) {
        container.insertBefore(alert, container.firstChild);
    } else {
        document.body.insertBefore(alert, document.body.firstChild);
    }
    
    // Автоудаление через 5 секунд
    setTimeout(() => {
        if (alert.parentNode) {
            alert.remove();
        }
    }, 5000);
}

// Category color mapping (should match category_mapping.json)
function getCategoryColor(category) {
    const colorMap = {
        'Запрещенные слова': 'danger',
        'Иностранные слова': 'warning',
        'Разрешенные иностранные термины': 'info',
        'Нормативные слова': 'success',
        'Технические термины': 'purple',
        'Топонимы': 'teal',
        'Аббревиатуры': 'orange',
        'Профессионализмы и жаргон': 'pink',
        'Термины': 'secondary',
        'Другие словари': 'light'
    };
    return colorMap[category] || 'secondary';
}

// Экспорт функций в глобальную область
window.syncAll = syncAll;
window.loadSyncStatus = loadSyncStatus;
window.uploadDictionary = uploadDictionary;
window.deleteDictionary = deleteDictionary;
window.exportDictionary = exportDictionary;
window.loadUserDictionaries = loadUserDictionaries;
window.loadAllDictionariesStatus = loadAllDictionariesStatus;
window.loadSources = loadSources;
window.logout = logout;
window.downloadTemplate = downloadTemplate;

// Запуск инициализации
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}
