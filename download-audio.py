#!/usr/bin/env python3
import os
import argparse
import yt_dlp
import sys
import time
import ssl
import shutil

def print_ssl_info():
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"🔒 OpenSSL: {ssl.OPENSSL_VERSION}")
    print()

def get_uploader(info):
    for key in ['uploader', 'channel', 'uploader_name', 'artist']:
        if info.get(key):
            return info[key]
    return 'Unknown'

def set_metadata(filepath, info, source):
    try:
        from mutagen.mp4 import MP4, MP4Cover
        audio = MP4(filepath)
        uploader = get_uploader(info)
        title = info.get('title', 'Unknown')

        audio['\xa9ART'] = [source]
        audio['\xa9alb'] = [uploader]
        audio['\xa9nam'] = [f"{uploader} - {title}"]

        if info.get('upload_date'):
            year = info['upload_date'][:4]
            audio['\xa9day'] = [year]

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
        print(f"   ✅ Метаданные установлены:")
        print(f"      • Исполнитель: {source}")
        print(f"      • Альбом: {uploader}")
        print(f"      • Название: {uploader} - {title}")
    except Exception as e:
        print(f"   ⚠️  Ошибка метаданных: {e}")

def download_audio(url, output_path, use_tor=False, debug=False):
    if 'youtube.com' in url or 'youtu.be' in url:
        source = 'youtube'
    elif 'rutube.ru' in url:
        source = 'rutube'
    else:
        source = 'audio'

    # 🔑 Оптимальные настройки для музыки (БЕЗ прокси):
    ydl_opts = {
        # Формат 18 (360p mp4) — надёжный выбор для музыки
        'format': '18/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_path, f'{source}_%(title)s.%(ext)s'),
        'writethumbnail': True,
        'quiet': False,
        'no_warnings': False,
        'retries': 3,
        'fragment_retries': 3,
        'socket_timeout': 10,
        'sleep_interval': 1,
        'extractor_args': {
            'youtube': {
                # web_safari предоставляет стабильные потоки без PO Token
                'player_client': ['web_safari', 'web'],
                'player_skip': [],
            }
        },
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192',
        }, {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
        # 🔑 Исправление ошибки с remote_components:
        'remote_components': 'ejs:github',  # СТРОКА, а не словарь!
    }

    if debug:
        ydl_opts['verbose'] = True

    ydl_opts['cookiesfrombrowser'] = ('firefox',)
    print("   🍪 Используем куки из Firefox")

    if use_tor:
        ydl_opts['proxy'] = 'socks5://127.0.0.1:9050'
        print("   ⚠️  ВНИМАНИЕ: прокси часто блокирует музыку из-за региональных ограничений")
        print("   🔌 Используем Tor (SOCKS5 127.0.0.1:9050)")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        base = os.path.join(output_path, f"{source}_{info['title']}")
        filename = base + '.m4a'

        if not os.path.exists(filename):
            for ext in ['.m4a', '.mp3', '.opus']:
                candidate = base + ext
                if os.path.exists(candidate):
                    if ext != '.m4a':
                        new_name = base + '.m4a'
                        os.rename(candidate, new_name)
                        filename = new_name
                    break

        if os.path.exists(filename):
            set_metadata(filename, info, source)
        return filename

if __name__ == "__main__":
    print_ssl_info()

    parser = argparse.ArgumentParser(description='Скачивание аудио (музыкальные клипы БЕЗ прокси)')
    parser.add_argument('url', type=str, help='URL видео')
    parser.add_argument('--output', '-o', type=str, default='downloads',
                        help='Папка для сохранения файлов (по умолчанию: downloads)')
    parser.add_argument('--tor', action='store_true',
                        help='Использовать Tor прокси (НЕ рекомендуется для музыки!)')
    parser.add_argument('--debug', action='store_true',
                        help='Включить подробный отладочный вывод')

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    # Проверка зависимостей
    try:
        from mutagen.mp4 import MP4
    except ImportError:
        print("❌ Установите зависимости: pip install mutagen")
        sys.exit(1)

    if not shutil.which('ffmpeg'):
        print("❌ Установите FFmpeg: brew install ffmpeg")
        sys.exit(1)

    print(f"🎯 Цель: {args.url}\n")

    # 🔑 Автоматическое отключение прокси для музыкальных клипов YouTube
    if 'youtube.com' in args.url or 'youtu.be' in args.url:
        if args.tor:
            print("⚠️  ВНИМАНИЕ: для музыкальных клипов прокси часто вызывает ошибки")
            print("   Рекомендуется запускать БЕЗ --tor\n")
        else:
            print("💡 Совет: для музыки прокси НЕ требуется (ваш регион имеет лицензию)\n")

    start_time = time.time()
    try:
        audio_file = download_audio(
            args.url,
            args.output,
            use_tor=args.tor,
            debug=args.debug
        )
        elapsed = time.time() - start_time
        print(f"\n✅ Успешно за {elapsed:.1f} сек | {os.path.basename(audio_file)}")
        sys.exit(0)

    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")

        if 'format is not available' in str(e).lower():
            print("\n💡 Ключевая причина ошибки с прокси:")
            print("  YouTube блокирует музыкальные клипы при смене региона.")
            print("  Tor меняет ваш IP на случайный узел (часто без лицензии на музыку).")
            print("\n✅ Решение — скачивать музыку БЕЗ прокси:")
            print(f"   python download-audio.py '{args.url}' -o {args.output}")
            print("\n🔍 Проверка лицензии в вашем регионе:")
            print("   Откройте видео в браузере БЕЗ прокси — если воспроизводится,")
            print("   значит ваш регион имеет лицензию и прокси НЕ нужен.")

        sys.exit(1)
