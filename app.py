from flask import Flask, request, render_template_string
import subprocess
import os
import tempfile
from faster_whisper import WhisperModel
import imageio_ffmpeg

app = Flask(__name__)

# Load model ONCE at startup with 4 CPU threads
model = WhisperModel('tiny', device='cpu', compute_type='int8', cpu_threads=4)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TikTok Transcriber</title>
<link href="https://fonts.googleapis.com/css2?family=Grenze+Gotisch:wght@400;700;900&family=Cinzel:wght@400;700&family=Crimson+Text:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: #0a0a0a;
    color: #c8c0b8;
    font-family: 'Crimson Text', Georgia, serif;
    min-height: 100vh;
    overflow-x: hidden;
  }

  body::before {
    content: '';
    position: fixed;
    inset: 0;
    background:
      radial-gradient(ellipse at 50% 0%, rgba(180, 20, 20, 0.07) 0%, transparent 55%),
      radial-gradient(ellipse at 80% 90%, rgba(120, 10, 10, 0.05) 0%, transparent 40%);
    pointer-events: none;
  }

  body::after {
    content: '';
    position: fixed;
    inset: 0;
    opacity: 0.035;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    pointer-events: none;
  }

  .container {
    position: relative;
    z-index: 1;
    max-width: 660px;
    margin: 0 auto;
    padding: 60px 24px 80px;
  }

  .header {
    text-align: center;
    margin-bottom: 48px;
    animation: fadeIn 1s ease-out;
  }

  .header h1 {
    font-family: 'Grenze Gotisch', serif;
    font-weight: 900;
    font-size: 4rem;
    color: #e8e0d8;
    letter-spacing: 3px;
    line-height: 1;
    text-shadow: 0 0 60px rgba(200, 30, 30, 0.2), 0 2px 4px rgba(0,0,0,0.5);
  }

  .header .subtitle {
    font-family: 'Cinzel', serif;
    font-size: 0.7rem;
    letter-spacing: 6px;
    text-transform: uppercase;
    color: #8a1a1a;
    margin-top: 14px;
  }

  .divider {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    margin: 0 auto 40px;
    color: #8a1a1a;
    font-size: 12px;
    opacity: 0.7;
  }

  .divider::before, .divider::after {
    content: '';
    width: 80px;
    height: 1px;
    background: linear-gradient(90deg, transparent, #8a1a1a, transparent);
  }

  .card {
    background: #0f0f0f;
    border: 1px solid #1f1f1f;
    padding: 40px 36px;
    position: relative;
    animation: slideUp 0.8s ease-out 0.2s both;
  }

  .card::before {
    content: '';
    position: absolute;
    top: -1px; left: 15%; right: 15%;
    height: 1px;
    background: linear-gradient(90deg, transparent, #8a1a1a, transparent);
  }

  .card::after {
    content: '';
    position: absolute;
    bottom: -1px; left: 15%; right: 15%;
    height: 1px;
    background: linear-gradient(90deg, transparent, #3a1010, transparent);
  }

  .corner {
    position: absolute;
    color: #2a1010;
    font-family: 'Grenze Gotisch', serif;
    font-size: 22px;
    line-height: 1;
    opacity: 0.5;
  }
  .corner-tl { top: 6px; left: 10px; }
  .corner-tr { top: 6px; right: 10px; transform: scaleX(-1); }
  .corner-bl { bottom: 6px; left: 10px; transform: scaleY(-1); }
  .corner-br { bottom: 6px; right: 10px; transform: scale(-1); }

  .input-label {
    font-family: 'Cinzel', serif;
    font-size: 0.65rem;
    letter-spacing: 4px;
    text-transform: uppercase;
    color: #5a5550;
    display: block;
    margin-bottom: 12px;
  }

  .url-input {
    width: 100%;
    background: #080808;
    border: 1px solid #1a1a1a;
    color: #e0dcd6;
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.05rem;
    padding: 14px 18px;
    outline: none;
    transition: border-color 0.3s ease, box-shadow 0.3s ease;
  }

  .url-input::placeholder {
    color: #3a3835;
    font-style: italic;
  }

  .url-input:focus {
    border-color: #5a1515;
    box-shadow: 0 0 20px rgba(180, 30, 30, 0.06), inset 0 0 30px rgba(180, 30, 30, 0.02);
  }

  .btn-transcribe {
    display: block;
    width: 100%;
    margin-top: 20px;
    padding: 16px 24px;
    background: #8a1a1a;
    color: #e8e0d8;
    font-family: 'Grenze Gotisch', serif;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 4px;
    text-transform: uppercase;
    border: 1px solid #a82020;
    border-bottom-color: #5a1010;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }

  .btn-transcribe:hover {
    background: #a82020;
    box-shadow: 0 0 40px rgba(180, 30, 30, 0.2), 0 4px 20px rgba(0,0,0,0.4);
    transform: translateY(-1px);
  }

  .btn-transcribe:active {
    transform: translateY(0);
    background: #701515;
  }

  .btn-transcribe:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  .btn-transcribe.loading { pointer-events: none; }

  .btn-transcribe.loading::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent);
    animation: shimmer 1.5s infinite;
  }

  .progress-wrap {
    margin-top: 24px;
    display: none;
  }

  .progress-wrap.visible { display: block; }

  .progress-bar {
    width: 100%;
    height: 2px;
    background: #1a1a1a;
    overflow: hidden;
  }

  .progress-bar-inner {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #5a1515, #b82020);
    animation: indeterminate 2s ease-in-out infinite;
  }

  .progress-text {
    font-family: 'Cinzel', serif;
    font-size: 0.6rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #5a5550;
    text-align: center;
    margin-top: 10px;
    animation: pulse 2s ease-in-out infinite;
  }

  .result-section {
    margin-top: 32px;
    display: none;
    animation: fadeIn 0.6s ease-out;
  }

  .result-section.visible { display: block; }

  .result-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
  }

  .result-label {
    font-family: 'Grenze Gotisch', serif;
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: 2px;
    color: #b82020;
  }

  .btn-copy {
    background: none;
    border: 1px solid #1f1f1f;
    color: #5a5550;
    font-family: 'Cinzel', serif;
    font-size: 0.6rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    padding: 6px 14px;
    cursor: pointer;
    transition: all 0.3s ease;
  }

  .btn-copy:hover {
    border-color: #5a1515;
    color: #b82020;
  }

  .result-box {
    background: #080808;
    border: 1px solid #1a1a1a;
    padding: 24px;
    font-family: 'Crimson Text', Georgia, serif;
    font-size: 1.05rem;
    line-height: 1.75;
    color: #c8c0b8;
    max-height: 400px;
    overflow-y: auto;
    white-space: pre-wrap;
  }

  .result-box::-webkit-scrollbar { width: 4px; }
  .result-box::-webkit-scrollbar-track { background: #080808; }
  .result-box::-webkit-scrollbar-thumb { background: #2a1010; }

  .error-msg {
    margin-top: 16px;
    padding: 14px 18px;
    background: rgba(180, 30, 30, 0.08);
    border: 1px solid rgba(180, 30, 30, 0.2);
    color: #d43030;
    font-size: 0.95rem;
    display: none;
    animation: fadeIn 0.3s ease-out;
  }

  .error-msg.visible { display: block; }

  .footer {
    text-align: center;
    margin-top: 48px;
    animation: fadeIn 1s ease-out 0.6s both;
  }

  .footer-text {
    font-family: 'Cinzel', serif;
    font-size: 0.55rem;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #3a3835;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @keyframes shimmer {
    to { left: 100%; }
  }

  @keyframes indeterminate {
    0% { width: 0%; margin-left: 0; }
    50% { width: 60%; margin-left: 20%; }
    100% { width: 0%; margin-left: 100%; }
  }

  @keyframes pulse {
    0%, 100% { opacity: 0.5; }
    50% { opacity: 1; }
  }

  @media (max-width: 600px) {
    .container { padding: 40px 16px 60px; }
    .header h1 { font-size: 2.8rem; }
    .card { padding: 28px 20px; }
  }
</style>
</head>
<body>

<div class="container">

  <div class="header">
    <h1>TikTok Transcriber</h1>
    <div class="subtitle">Unveil the spoken word</div>
  </div>

  <div class="divider">&#10013;</div>

  <div class="card">
    <span class="corner corner-tl">&#9766;</span>
    <span class="corner corner-tr">&#9766;</span>
    <span class="corner corner-bl">&#9766;</span>
    <span class="corner corner-br">&#9766;</span>

    <label class="input-label" for="url">Paste the URL</label>
    <input
      class="url-input"
      type="text"
      id="url"
      placeholder="https://www.tiktok.com/..."
      autocomplete="off"
      spellcheck="false"
    />

    <button class="btn-transcribe" id="transcribeBtn" onclick="transcribe()">
      Transcribe
    </button>

    <div class="error-msg" id="error"></div>

    <div class="progress-wrap" id="progress">
      <div class="progress-bar"><div class="progress-bar-inner"></div></div>
      <div class="progress-text">Transcribing &hellip;</div>
    </div>

    <div class="result-section" id="resultSection">
      <div class="result-header">
        <span class="result-label">Transcription</span>
        <button class="btn-copy" onclick="copyText()">Copy</button>
      </div>
      <div class="result-box" id="resultBox"></div>
    </div>
  </div>

  <div class="footer">
    <div class="footer-text">Dalton's Transcriber &#8212; MMXXVI</div>
  </div>

</div>

<script>
async function transcribe() {
  const url = document.getElementById('url').value.trim();
  const btn = document.getElementById('transcribeBtn');
  const progress = document.getElementById('progress');
  const resultSection = document.getElementById('resultSection');
  const resultBox = document.getElementById('resultBox');
  const error = document.getElementById('error');

  error.classList.remove('visible');
  resultSection.classList.remove('visible');

  if (!url) {
    error.textContent = 'A URL is required to proceed.';
    error.classList.add('visible');
    return;
  }

  btn.classList.add('loading');
  btn.disabled = true;
  btn.textContent = 'Working...';
  progress.classList.add('visible');

  try {
    const response = await fetch('/transcribe', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url })
    });

    const data = await response.json();

    if (data.error) {
      error.textContent = data.error;
      error.classList.add('visible');
    } else {
      resultBox.textContent = data.transcript;
      resultSection.classList.add('visible');
    }
  } catch (err) {
    error.textContent = 'Something went wrong. Please try again.';
    error.classList.add('visible');
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
    btn.textContent = 'Transcribe';
    progress.classList.remove('visible');
  }
}

function copyText() {
  const text = document.getElementById('resultBox').textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.querySelector('.btn-copy');
    btn.textContent = 'Copied';
    setTimeout(() => btn.textContent = 'Copy', 2000);
  });
}

document.getElementById('url').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') transcribe();
});
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
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, 'audio.%(ext)s')

            subprocess.run([
                'yt-dlp',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                '-x',
                '--audio-format', 'wav',
                '--audio-quality', '5',
                '--ffmpeg-location', ffmpeg_path,
                '-o', audio_path,
                url
            ], check=True)

            wav_path = os.path.join(tmpdir, 'audio.wav')

            segments, _ = model.transcribe(
                wav_path,
                beam_size=1,
                vad_filter=True,
                condition_on_previous_text=False
            )
            transcript = ' '.join([s.text for s in segments])

            return {'transcript': transcript}
    except Exception as e:
        return {'error': str(e)}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
