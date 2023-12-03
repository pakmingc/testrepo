from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import sys
import os
import re
import glob
from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL

def download_subs(video_id, language='en'):  # 預設語言設為英文
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        primary_transcript = None

        # 優先尋找英文字幕
        try:
            primary_transcript = transcript_list.find_transcript(['en'])
        except:
            pass

        # 如果沒有找到英文字幕，嘗試其他語言
        if not primary_transcript:
            try:
                primary_transcript = transcript_list.find_transcript([
                    'yue', 'yue-HK', 'zh', 'zh-HK', 'zh-CN', 'zh-Hans',
                    'zh-SG', 'zh-Hant', 'zh-TW'
                ])
            except:
                print("沒有英文或中文字幕可用。")
                return None

        # 提取字幕
        subs = [line['text'] for line in primary_transcript.fetch()]
        return '\n'.join(subs)

    except Exception as e:
        print(f"下載字幕失敗: {e}")
        return None

def get_video_title(video_id):
    ydl_opts = {}
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(video_id, download=False)
        return info_dict.get('title', None)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download', methods=['POST', 'GET'])
def download():
    message = ""
    if request.method == 'POST':
        video_url_or_id = request.form['video_url']
        video_id = re.search(r'(?<=v=)[^&#]+', video_url_or_id)
        video_id = video_id.group(0) if video_id else video_url_or_id

        if not video_id.startswith('http'):
            video_id = re.search(r'(?<=youtu\.be/)[^&#]+', video_url_or_id)
            video_id = video_id.group(0) if video_id else video_url_or_id

        title = get_video_title(video_id)
        if not title:
            return redirect(url_for('index'))

        subs = download_subs(video_id)
        if subs:
            date_folder = datetime.now().strftime("%Y-%m-%d")
            save_folder = os.path.join('static', 'subtitles', date_folder)
            if not os.path.exists(save_folder):
                os.makedirs(save_folder)

            save_path = os.path.join(save_folder, f"{title}.txt")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(subs)

            message = f"字幕已儲存到: {save_path}"

    # 搜集當天保存的字幕文件
    today_date = datetime.now().strftime("%Y-%m-%d")
    today_folder = os.path.join('static', 'subtitles', today_date)
    files_info = []
    if os.path.exists(today_folder):
        for file in glob.glob(os.path.join(today_folder, "*.txt")):
            file_name = os.path.basename(file)
            file_time = datetime.fromtimestamp(os.path.getmtime(file)).strftime('%H:%M:%S')

            files_info.append({
                'date': today_date,
                'time': file_time,
                'name': file_name
            })

    # 在返回渲染模板之前，按時間排序文件信息
    files_info.sort(key=lambda x: x['time'], reverse=True)

    return render_template('download.html', message=message, files=files_info)

if __name__ == '__main__':
    app.run(debug=True)
