#!/usr/bin/env python3
import os
import argparse
import yt_dlp
import sys
from mutagen.mp4 import MP4, MP4Cover

def get_uploader(info):
    """Получает название канала/автора"""
    for key in ['uploader', 'channel', 'uploader_name', 'artist']:
        if info.get(key):
            return info[key]
    return 'Unknown'

def set_metadata(filepath, info, source):
    """Устанавливает кастомные метаданные в m4a файл"""
    try:
        audio = MP4(filepath)
        uploader = get_uploader(info)
        title = info.get('title', 'Unknown')

        audio['\xa9ART'] = [source]                      # Исполнитель
        audio['\xa9alb'] = [uploader]                    # Альбом
        audio['\xa9nam'] = [f"{uploader} - {title}"]     # Название

        if info.get('upload_date'):
            year = info['upload_date'][:4]
            audio['\xa9day'] = [year]

        # Встраиваем обложку
        base = os.path.splitext(filepath)[0]
        for ext in ['.jpg', '.jpeg', '.webp', '.png']:
            thumb_path = base + ext
            if os.path.exists(thumb_path):
                with open(thumb_path, 'rb') as f:
                    cover_data = f.read()
                cover_format = MP4Cover.FORMAT_JPEG if ext in ['.jpg', '.jpeg'] else MP4Cover.FORMAT_PNG
                audio['covr'] = [MP4Cover(cover_data, imageformat=cover_format)]
                os.remove(thumb_path)
                break

        audio.save()
        print(f"   Метаданные установлены:")
        print(f"     • Исполнитель: {source}")
        print(f"     • Альбом: {uploader}")
        print(f"     • Название: {uploader} - {title}")

    except Exception as e:
        print(f"   ⚠️  Не удалось установить метаданные: {e}")

def download_audio(url, output_path, use_cookies=False, use_proxy=False):
    """Скачивает аудио с автоматическим выбором лучшего потока"""
    # Определяем источник
    if 'youtube.com' in url or 'youtu.be' in url:
        source = 'youtube'
    elif 'rutube.ru' in url:
        source = 'rutube'
    else:
        source = 'audio'

    ydl_opts = {
        # Наилучший аудио-поток с резервным вариантом из видео
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_path, f'{source}_%(title)s.%(ext)s'),
        'writethumbnail': True,
        'quiet': False,
        'no_warnings': True,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 10,
        'socket_timeout': 30,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192',  # Оптимальное качество
        }, {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
    }

    # Добавляем куки если нужно
    if use_cookies:
        ydl_opts['cookiesfrombrowser'] = ('firefox',)
        print("🍪 Используем cookies из Firefox для обхода защиты")

    # Добавляем прокси если нужно
    if use_proxy:
        ydl_opts['proxy'] = 'socks5://127.0.0.1:9050'
        print("🔌 Используем SOCKS5 прокси 127.0.0.1:9050")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base = os.path.join(output_path, f"{source}_{info['title']}")
        filename = base + '.m4a'

        # Устанавливаем метаданные
        if os.path.exists(filename):
            set_metadata(filename, info, source)
        else:
            for ext in ['.m4a', '.mp3', '.opus']:
                candidate = base + ext
                if os.path.exists(candidate):
                    if ext != '.m4a':
                        new_name = base + '.m4a'
                        os.rename(candidate, new_name)
                        filename = new_name
                    set_metadata(filename, info, source)
                    break

        return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Скачивание аудио с автоматическим обходом ограничений')
    parser.add_argument('url', type=str, help='URL видео')
    parser.add_argument('--output', '-o', type=str, default='downloads',
                        help='Папка для сохранения файлов (по умолчанию: downloads)')
    parser.add_argument('--cookies', action='store_true',
                        help='Принудительно использовать cookies из Firefox')
    parser.add_argument('--proxy', action='store_true',
                        help='Принудительно использовать SOCKS5 прокси 127.0.0.1:9050')

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    # Проверка зависимостей
    try:
        from mutagen.mp4 import MP4
    except ImportError:
        print("❌ Требуется библиотека mutagen")
        print("   Установите: pip install mutagen")
        sys.exit(1)

    import shutil
    if not shutil.which('ffmpeg'):
        print("❌ Требуется FFmpeg")
        print("   Установите: brew install ffmpeg")
        sys.exit(1)

    try:
        print(f"Обработка: {args.url}")
        # Первая попытка без куков и прокси
        if not args.cookies and not args.proxy:
            try:
                audio_file = download_audio(args.url, args.output, use_cookies=False, use_proxy=False)
            except Exception as e:
                error_msg = str(e).lower()
                # Обнаружение ошибок защиты от ботов
                if 'sign in to confirm' in error_msg or 'bot' in error_msg or 'captcha' in error_msg:
                    print("\n⚠️  Обнаружена защита от ботов. Повторная попытка с cookies из Firefox...")
                    audio_file = download_audio(args.url, args.output, use_cookies=True, use_proxy=False)
                # Обнаружение сетевых ошибок
                elif 'timeout' in error_msg or 'connection' in error_msg or 'unable to connect' in error_msg:
                    print("\n⚠️  Сетевая ошибка. Повторная попытка через SOCKS5 прокси...")
                    audio_file = download_audio(args.url, args.output, use_cookies=False, use_proxy=True)
                else:
                    raise
        else:
            # Принудительное использование опций
            audio_file = download_audio(
                args.url,
                args.output,
                use_cookies=args.cookies,
                use_proxy=args.proxy
            )

        print(f"\n✅ Аудио сохранено: {os.path.basename(audio_file)}")

    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        sys.exit(1)
