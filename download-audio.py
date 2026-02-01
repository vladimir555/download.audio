#!/usr/bin/env python3

import os
import argparse
import yt_dlp
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

def download_audio(url, output_path):
    """Скачивает ТОЛЬКО аудио без видео с гибкой обработкой форматов"""
    # Определяем источник
    if 'youtube.com' in url or 'youtu.be' in url:
        source = 'youtube'
    elif 'rutube.ru' in url:
        source = 'rutube'
    else:
        source = 'audio'

    ydl_opts = {
        # Гибкий выбор формата: лучший аудио-только поток, или аудио из видео
        'format': 'bestaudio[acodec!=none]/bestaudio/best',
        'outtmpl': os.path.join(output_path, f'{source} %(title)s.%(ext)s'),
        'writethumbnail': True,
        'quiet': False,
        'no_warnings': True,
        # Конвертируем в m4a после загрузки (гарантируем нужный формат)
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '0',  # 0 = без потерь качества (копирование)
        }, {
            'key': 'FFmpegMetadata',
            'add_metadata': True,
        }],
        # Отключаем строгую фильтрацию видео — yt-dlp сам извлечет аудио
        'format_sort': [],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        # После конвертации в m4a файл будет с расширением .m4a
        base = os.path.join(output_path, f"{source} {info['title']}")
        filename = base + '.m4a'

        # Устанавливаем кастомные метаданные (перезаписываем стандартные)
        if os.path.exists(filename):
            set_metadata(filename, info, source)
        else:
            # Иногда yt-dlp оставляет оригинальное расширение перед конвертацией
            for ext in ['.m4a', '.mp4', '.webm', '.opus']:
                candidate = base + ext
                if os.path.exists(candidate):
                    if ext != '.m4a':
                        # Переименовываем в .m4a
                        new_name = base + '.m4a'
                        os.rename(candidate, new_name)
                        filename = new_name
                    set_metadata(filename, info, source)
                    break

        return filename

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Скачивание ТОЛЬКО аудио без видео')
    parser.add_argument('url', type=str, help='URL видео')
    parser.add_argument('--output', '-o', type=str, default='downloads',
                        help='Папка для сохранения файлов (по умолчанию: downloads)')

    args = parser.parse_args()
    os.makedirs(args.output, exist_ok=True)

    # Проверка зависимостей
    try:
        from mutagen.mp4 import MP4
    except ImportError:
        print("❌ Требуется библиотека mutagen")
        print("   Установите: pip install mutagen")
        exit(1)

    # Проверка FFmpeg (обязателен для конвертации в m4a)
    import shutil
    if not shutil.which('ffmpeg'):
        print("❌ Требуется FFmpeg для конвертации аудио")
        print("   Установите: brew install ffmpeg  # macOS")
        print("   Или: sudo apt install ffmpeg    # Linux")
        exit(1)

    try:
        print(f"Обработка: {args.url}")
        audio_file = download_audio(args.url, args.output)
        print(f"\n✅ Аудио сохранено (ТОЛЬКО звук): {os.path.basename(audio_file)}")
        print(f"   Путь: {audio_file}")

    except yt_dlp.utils.DownloadError as e:
        if 'format is not available' in str(e).lower():
            print("\n⚠️  Формат не найден. Доступные форматы:")
            # Показываем доступные форматы
            ydl_opts = {'listformats': True, 'quiet': False}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([args.url])
        else:
            print(f"\n❌ Ошибка: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        exit(1)
