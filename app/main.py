#!/usr/bin/env python3
"""
FastAPI микросервис для проверки текста на соответствие закону № 168-ФЗ
"""

import json
import os
import re
import tempfile
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form, Depends
from typing import List, Optional
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Админский ключ для доступа к админ-панели
ADMIN_KEY = os.getenv('ADMIN_KEY', 'admin123')

# Импорты из текущего проекта
from extractors import TextExtractor
from checker import LanguageChecker
from dictionaries.manager import DictionaryManager
from sync import DictionarySynchronizer, OFFICIAL_DICTIONARIES
from reporter import ReportGenerator

# Создание FastAPI приложения
app = FastAPI(
    title="168-ФЗ Text Checker",
    description="Микросервис для проверки текстов на соответствие закону № 168-ФЗ 'О защите русского языка'",
    version="1.2.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статические файлы и шаблоны
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")
templates = Jinja2Templates(directory="app/web/templates")

# Глобальные менеджеры
dictionaries_dir = Path(os.getenv('DICTIONARIES_DIR', 'dictionaries/data'))
synchronizer = DictionarySynchronizer(
    data_dir=dictionaries_dir,
    cache_dir=Path('sync/cache')
)
# Передаем метаданные синхронизации в DictionaryManager для отображения статуса
dict_manager = DictionaryManager(dictionaries_dir, synchronizer.metadata)
checker = LanguageChecker(dictionaries_dir)
# Обновляем checker.dict_manager, чтобы он тоже имел доступ к метаданным
checker.dict_manager = dict_manager


@app.on_event("startup")
async def startup_event():
    """Автоматическая синхронизация словарей при запуске приложения"""
    from threading import Thread
    
    # Запускаем синхронизацию в отдельном потоке, чтобы не блокировать старт сервера
    def sync_in_background():
        try:
            print("Проверка и синхронизация словарей при запуске...")
            # Всегда выполняем проверку и синхронизацию официальных словарей
            # (sync_all с force=False сам проверит, нужны ли обновления)
            results = synchronizer.sync_all(force=False)
            success_count = sum(1 for success, _ in results.values() if success)
            total_count = len(results)
            print(f"Проверка синхронизации завершена: {success_count}/{total_count} словарей актуальны")
            
            # Если были загружены новые словари, перезагружаем их в менеджер
            if any(success for success, _ in results.values()):
                dict_manager.reload_dictionaries()
                checker.dict_manager.reload_dictionaries()
                print("Новые словари загружены в память.")
        except Exception as e:
            print(f"Ошибка при автоматической синхронизации словарей: {e}")
    
    # Запускаем в отдельном потоке, чтобы не блокировать старт
    thread = Thread(target=sync_in_background, daemon=True)
    thread.start()


# ==================== AUTHENTICATION ====================

def verify_admin_key(request: Request):
    """
    Проверка админ-ключа.
    Ключ можно передать либо в заголовке X-Admin-Key, либо в query параметре admin_key
    """
    admin_key = request.headers.get('X-Admin-Key') or request.query_params.get('admin_key')
    
    if not admin_key:
        raise HTTPException(
            status_code=401,
            detail="Требуется аутентификация. Передайте ключ в заголовке X-Admin-Key или параметре admin_key"
        )
    
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=403,
            detail="Неверный админ-ключ"
        )
    
    return True


# ==================== API ENDPOINTS ====================

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница с веб-интерфейсом (публичная)"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    """Админ-панель с управлением словарями и синхронизацией"""
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/robots.txt", response_class=FileResponse)
async def robots_txt():
    """robots.txt файл"""
    return FileResponse("app/web/static/robots.txt", media_type="text/plain")


@app.post("/api/v1/check")
async def check_text(request: Request):
    """
    Проверка текста на соответствие закону 168-ФЗ
    
    Принимает JSON с полями:
    - text: прямой текст для проверки
    - url: URL страницы для извлечения и проверки
    - allowed_words: (опционально) список дополнительных разрешенных иностранных слов
    
    Returns:
        Детальный отчет со всеми словами текста
    """
    try:
        data = await request.json()
        text = data.get('text', '').strip()
        url = data.get('url', '').strip()
        allowed_words = data.get('allowed_words', [])
        source_info = None
        
        if not text and not url:
            raise HTTPException(status_code=400, detail="Укажите текст или URL для проверки")
        
        # Если передан URL, извлекаем текст
        if url:
            extractor = TextExtractor(url)
            text = extractor.get_text()
            source_info = {
                "type": "url",
                "url": url,
                "chars_extracted": len(text),
                "words_extracted": len(text.split())
            }
            if not text.strip():
                raise HTTPException(status_code=400, detail="Не удалось извлечь текст из URL")
        
        # Проверка текста
        results = checker.check_text(text, allowed_words=allowed_words)
        
        # Добавляем информацию об источнике
        if source_info:
            results['source_info'] = source_info
        
        
        return JSONResponse({
            "success": True,
            "data": results
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/check/file")
async def check_file(
    file: UploadFile = File(...),
    allowed_words: Optional[str] = Form(None)
):
    """
    Проверка текста из загруженного файла
    
    Поддерживаемые форматы: .txt, .md, .html, .json, .csv
    
    Returns:
        Детальный отчет со всеми словами файла
    """
    try:
        # Проверяем расширение файла
        allowed_extensions = {'.txt', '.md', '.html', '.htm', '.json', '.csv'}
        file_ext = Path(file.filename).suffix.lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Неподдерживаемый формат файла. Поддерживаются: {', '.join(allowed_extensions)}"
            )
        
        # Читаем файл
        content = await file.read()
        
        # Сохраняем во временный файл для TextExtractor
        with tempfile.NamedTemporaryFile(mode='wb', suffix=file_ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Извлекаем текст
            extractor = TextExtractor(tmp_path)
            text = extractor.get_text()
            
            if not text.strip():
                raise HTTPException(status_code=400, detail="Файл пустой или не содержит текста")
            
            # Парсим allowed_words если передано
            allowed_words_list = None
            if allowed_words:
                try:
                    allowed_words_list = json.loads(allowed_words)
                except json.JSONDecodeError:
                    # Если не валидный JSON, пробуем как строку с разделителями
                    allowed_words_list = [w.strip() for w in allowed_words.replace(',', ' ').split() if w.strip()]
            
            # Проверяем текст с учетом разрешенных слов
            results = checker.check_text(text, allowed_words=allowed_words_list)
            
            # Добавляем информацию о файле
            results['source_info'] = {
                "type": "file",
                "filename": file.filename,
                "file_size": len(content),
                "chars_extracted": len(text),
                "words_extracted": len(text.split())
            }
            
            
            return JSONResponse({
                "success": True,
                "data": results,
                "filename": file.filename
            })
        finally:
            # Удаляем временный файл
            Path(tmp_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка обработки файла: {str(e)}")


@app.get("/api/v1/dictionaries")
async def list_dictionaries():
    """Список всех загруженных словарей"""
    try:
        dictionaries = dict_manager.list_dictionaries()
        return JSONResponse({
            "success": True,
            "data": dictionaries
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dictionaries/{dict_name}")
async def get_dictionary_info(dict_name: str):
    """Информация о конкретном словаре"""
    try:
        info = dict_manager.get_dictionary_info(dict_name)
        if not info:
            raise HTTPException(status_code=404, detail=f"Словарь '{dict_name}' не найден")
        return JSONResponse({
            "success": True,
            "data": info
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/dictionaries/{dict_name}/words")
async def get_dictionary_words(dict_name: str, limit: int = 1000, search: str = None):
    """
    Получение слов из конкретного словаря
    
    Параметры query:
    - limit: ограничение количества возвращаемых слов (по умолчанию 1000, максимум 10000)
    - search: опциональный поисковый запрос для фильтрации слов (подстрока)
    """
    try:
        dict_data = dict_manager.get_dictionary_info(dict_name)
        if not dict_data:
            raise HTTPException(status_code=404, detail=f"Словарь '{dict_name}' не найден")
        
        # Получаем все слова из словаря
        full_dict = dict_manager.dictionaries.get(dict_name, {})
        words = list(full_dict.get('words', set()))
        mappings = full_dict.get('mappings', {})
        
        # Фильтруем если есть поисковый запрос
        if search:
            search_lower = search.lower()
            words = [w for w in words if search_lower in w.lower()]
        
        # Сортируем для удобства
        words.sort()
        
        # Применяем лимит
        total_count = len(words)
        if limit > 0:
            words = words[:limit]
        
        # Подготавливаем данные с mappings если они есть
        words_data = []
        for word in words:
            word_entry = {"word": word}
            if word in mappings:
                word_entry["mapping"] = mappings[word]
            words_data.append(word_entry)
        
        return JSONResponse({
            "success": True,
            "data": {
                "words": words_data,
                "total": total_count,
                "returned": len(words_data),
                "limited": limit > 0 and total_count > limit,
                "searched": search is not None,
                "has_mappings": len(mappings) > 0
            }
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/dictionaries/load")
async def load_dictionary(request: Request, admin_auth: bool = Depends(verify_admin_key)):
    """
    Загрузка дополнительного словаря (требуются права администратора)
    
    Принимает JSON: {"filepath": "путь/к/файлу.json", "name": "опциональное имя"}
    """
    try:
        data = await request.json()
        filepath = data.get('filepath')
        name = data.get('name')
        
        if not filepath:
            raise HTTPException(status_code=400, detail="Укажите filepath")
        
        path = Path(filepath)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Файл не найден: {filepath}")
        
        dict_name = dict_manager.load_dictionary(path, name)
        
        return JSONResponse({
            "success": True,
            "message": f"Словарь загружен: {dict_name}",
            "data": {"name": dict_name}
        })
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/allowed-foreign")
async def get_allowed_foreign():
    """Получение списка разрешенных иностранных слов"""
    try:
        # Получаем словарь allowed_foreign из dict_manager
        allowed_foreign_dict = dict_manager.dictionaries.get('allowed_foreign', {})
        words = list(allowed_foreign_dict.get('words', set()))
        words.sort()  # Сортируем для удобства отображения
        
        return JSONResponse({
            "success": True,
            "data": {
                "words": words,
                "count": len(words),
                "source": allowed_foreign_dict.get('source', 'unknown'),
                "version": allowed_foreign_dict.get('version', '1.0')
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sync/status")
async def get_sync_status():
    """Статус синхронизации всех словарей"""
    try:
        status = synchronizer.get_sync_status()
        return JSONResponse({
            "success": True,
            "data": status
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sync/all")
async def sync_all(
    request: Request,
    force: bool = False,
    admin_auth: bool = Depends(verify_admin_key)
):
    """Синхронизация всех словарей (требуются права администратора)"""
    try:
        results = synchronizer.sync_all(force)
        
        # Подсчитываем успешные/неуспешные
        success_count = sum(1 for success, _ in results.values() if success)
        total_count = len(results)
        
        return JSONResponse({
            "success": success_count == total_count,
            "message": f"Успешно: {success_count}/{total_count}",
            "data": {
                "results": {k: {"success": v[0], "message": v[1]} for k, v in results.items()}
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/sync/{dict_name}")
async def sync_dictionary(
    request: Request,
    dict_name: str,
    force: bool = False,
    admin_auth: bool = Depends(verify_admin_key)
):
    """
    Синхронизация конкретного словаря (требуются права администратора)
    
    Параметры query:
    - force: принудительная перезагрузка
    """
    try:
        if dict_name not in OFFICIAL_DICTIONARIES:
            # Проверяем, может быть это реальный источник
            from sync.sources import get_dictionary_source
            source = get_dictionary_source(dict_name)
            if not source:
                raise HTTPException(status_code=404, detail=f"Словарь '{dict_name}' не найден")
        
        success, message = synchronizer.sync_dictionary(dict_name, force)
        
        if success:
            return JSONResponse({
                "success": True,
                "message": message
            })
        else:
            raise HTTPException(status_code=500, detail=message)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/sources")
async def list_sources():
    """Список всех доступных источников словарей"""
    try:
        from sync.sources import list_available_sources
        sources = list_available_sources()
        return JSONResponse({
            "success": True,
            "data": sources
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return JSONResponse({
        "status": "healthy",
        "service": "168-ФЗ Text Checker",
        "version": "1.2.0"
    })


# ==================== ЗАПУСК СЕРВЕРА ====================

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    
    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
