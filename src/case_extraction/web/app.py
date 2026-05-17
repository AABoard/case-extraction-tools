"""Flask web app for file upload and extraction."""

import os
import secrets
import uuid
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string, send_file

from .config import get_web_config, get_upload_dir
from .upload_handler import UploadHandler


def create_app() -> Flask:
    """Factory for Flask app (injectable config)."""
    app = Flask(__name__)
    cfg = get_web_config()
    max_bytes = cfg.get("max_content_length", 50 * 1024 * 1024)
    if isinstance(max_bytes, int):
        app.config["MAX_CONTENT_LENGTH"] = max_bytes
    app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(16))

    upload_dir = get_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)

    handler = UploadHandler()

    @app.route("/")
    def index():
        return render_template_string(_INDEX_HTML)

    @app.route("/upload", methods=["POST"])
    def upload():
        if "file" not in request.files and "files" not in request.files:
            return jsonify({"error": "No file(s) provided"}), 400
        files = request.files.getlist("file") or request.files.getlist("files")
        if not files or (len(files) == 1 and not files[0].filename):
            return jsonify({"error": "No file(s) selected"}), 400

        results = []
        for f in files:
            if not f or not f.filename:
                continue
            if not handler.is_allowed(f.filename):
                results.append({
                    "filename": f.filename,
                    "success": False,
                    "error": f"Extension not allowed. Use: {', '.join(handler.allowed_extensions)}",
                })
                continue
            safe_name = f"{uuid.uuid4().hex}_{Path(f.filename).name}"
            save_path = upload_dir / safe_name
            try:
                f.save(str(save_path))
                upload_result = handler.process(save_path, f.filename)
                if upload_result.success:
                    outputs = {}
                    for fmt, p in upload_result.output_files.items():
                        outputs[fmt] = f"/download/{p.name}"
                    results.append({
                        "filename": f.filename,
                        "success": True,
                        "case_id": upload_result.case.get("case_id") if upload_result.case else None,
                        "downloads": outputs,
                    })
                else:
                    results.append({
                        "filename": f.filename,
                        "success": False,
                        "error": upload_result.error,
                    })
            except Exception as e:
                results.append({"filename": f.filename, "success": False, "error": str(e)})
            finally:
                if save_path.exists():
                    save_path.unlink(missing_ok=True)

        return jsonify({"results": results})

    @app.route("/download/<path:filename>")
    def download(filename: str):
        # Security: only serve from upload_dir, basename only
        name = Path(filename).name
        path = upload_dir / name
        if not path.exists() or not path.is_file():
            return jsonify({"error": "Not found"}), 404
        return send_file(path, as_attachment=True, download_name=name)

    return app


_INDEX_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AAB Case Extractor — Upload</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: system-ui, sans-serif; max-width: 600px; margin: 2rem auto; padding: 0 1rem; color: #1a202c; }
    h1 { color: #1a365d; font-size: 1.5rem; }
    .dropzone { border: 2px dashed #cbd5e0; border-radius: 8px; padding: 2rem; text-align: center; background: #f7fafc; cursor: pointer; margin: 1rem 0; }
    .dropzone:hover, .dropzone.dragover { border-color: #4299e1; background: #ebf8ff; }
    input[type="file"] { display: none; }
    button { background: #2b6cb0; color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; font-size: 1rem; }
    button:hover { background: #2c5282; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    #output { margin-top: 1.5rem; }
    .result { padding: 0.75rem; margin: 0.5rem 0; border-radius: 6px; }
    .result.success { background: #c6f6d5; }
    .result.fail { background: #fed7d7; }
    .result a { color: #2b6cb0; margin-right: 1rem; }
  </style>
</head>
<body>
  <h1>AAB Case Extractor</h1>
  <p>Select or drop files (PDF, DOCX, TXT, MD, HTML) to extract AAB case records.</p>
  <form id="form">
    <div class="dropzone" id="dropzone" onclick="document.getElementById('fileInput').click()">
      <input type="file" id="fileInput" name="file" multiple accept=".pdf,.docx,.doc,.txt,.md,.html">
      <p>Click or drag files here</p>
    </div>
    <button type="submit" id="btn">Extract</button>
  </form>
  <div id="output"></div>
  <script>
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');
    fileInput.onchange = () => { dropzone.querySelector('p').textContent = fileInput.files.length + ' file(s) selected'; };
    dropzone.ondragover = e => { e.preventDefault(); dropzone.classList.add('dragover'); };
    dropzone.ondragleave = () => dropzone.classList.remove('dragover');
    dropzone.ondrop = e => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
      fileInput.files = e.dataTransfer.files;
      dropzone.querySelector('p').textContent = fileInput.files.length + ' file(s) selected';
    };
    document.getElementById('form').onsubmit = async (e) => {
      e.preventDefault();
      const btn = document.getElementById('btn');
      btn.disabled = true;
      const fd = new FormData();
      for (const f of fileInput.files) fd.append('file', f);
      const out = document.getElementById('output');
      try {
        const r = await fetch('/upload', { method: 'POST', body: fd });
        const data = await r.json();
        out.innerHTML = (data.results || []).map(r => {
          if (r.success) {
            const links = Object.entries(r.downloads || {}).map(([fmt, url]) => `<a href="${url}">${fmt}</a>`).join('');
            return `<div class="result success">${r.filename}: OK — ${links}</div>`;
          }
          return `<div class="result fail">${r.filename}: ${r.error}</div>`;
        }).join('');
      } catch (err) {
        out.innerHTML = `<div class="result fail">Error: ${err.message}</div>`;
      }
      btn.disabled = false;
    };
  </script>
</body>
</html>
"""
