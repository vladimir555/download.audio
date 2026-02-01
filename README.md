# Загрузка аудио

Скачивает аудио с YouTube и Rutube в формате M4A с обложкой и метаданными.

## Запуск

### 1. Установите зависимости
```bash
pip install -r requirements.txt
```
### 2. Установите FFmpeg (обязательно)
#### macOS
```bash
brew install ffmpeg
```
#### Linux
```bash
sudo apt install ffmpeg
```

# 3. Запустите
```bash
python download-audio.py 'https://rutube.ru/video/...'
```
```bash
python download-audio.py 'https://youtube.com/watch?v=...' -o ./audio
```
