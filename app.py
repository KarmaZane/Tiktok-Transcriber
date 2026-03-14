from flask import Flask, request, render_template_string
import subprocess
import os
import tempfile
from faster_whisper import WhisperModel
import imageio_ffmpeg

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TikTok Transcriber</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; max-width: 700px; margin: 40px auto; padding: 0 20px; }
        input { width: 100%; padding: 10px; font-size: 16px; margin: 10px 0; box-sizing: border-box; }
        button { padding: 12px 24px; font-size: 16px; background: #000; color: #fff; border: none; cursor: pointer; }
        pre { background: #f4f4f4; padding: 20px; white-space: pre-wrap; word-wrap: break-word; }
        .error { color: red; }
    </style>
</head>
<body>
    <h1>TikTok Transcriber</h1>
    <input type="text" id="url" placeholder="Paste TikTok URL here..." />
    <button onclick="transcribe()">Transcribe</button>
    <p id="status"></p>
    <pre id="output"></pre>
    <script>
        async function transcribe() {
            const url = document.getElementById('url').value;
            document.getElementById('status').textContent = 'Working on it... this may take a minute.';
            document.getElementById('output').textContent = '';
            const res = await fetch('/transcribe', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({url})
            });
            const data = await res.json();
            document.getElementById('status').textContent = '';
            if (data.error) {
                document.getElementById('output').innerHTML = '<span class="error">' + data.error + '</span>';
            } else {
                document.getElementById('output').textContent = data.transcript;
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    url = request.json.get('url')
    if not url:
        return {'error': 'No URL provided'}
    try:
        # This grabs the absolute, guaranteed path to ffmpeg
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, 'audio.%(ext)s')
            
            subprocess.run([
                'yt-dlp', 
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                '-x', 
                '--audio-format', 'mp3', 
                '--ffmpeg-location', ffmpeg_path,
                '-o', audio_path, 
                url
            ], check=True)
            
            mp3_path = os.path.join(tmpdir, 'audio.mp3')
            
            model = WhisperModel('base', device='cpu', compute_type='int8')
            segments, _ = model.transcribe(mp3_path)
            transcript = ' '.join([s.text for s in segments])
            
            return {'transcript': transcript}
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
