import os
import json
import uuid
import hashlib
import markdown
import shutil
import tempfile
import zipfile
from datetime import datetime
from flask import Flask, render_template, request, jsonify, abort, redirect, url_for, send_file
from dominate import document
from dominate.tags import div
from dominate.util import raw

app = Flask(__name__)
app.config['DATA_DIR'] = os.path.join(os.path.dirname(__file__), 'data')

# 公共函数与类
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return value.strftime(format)

def str_to_datetime(date_str):
    return datetime.fromisoformat(date_str)

def serialize_object(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_object(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_object(item) for item in obj]
    else:
        return obj

def compute_hash(content):
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

# Image 类与存储
class Image:
    def __init__(self, filename, url):
        self.id = uuid.uuid4().hex
        self.filename = filename
        self.url = url
        self.uploaded_at = datetime.now().isoformat()

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "url": self.url,
            "uploaded_at": self.uploaded_at
        }

class ImageStorage:
    def __init__(self, filename=None):
        self.filename = filename or os.path.join(app.config['DATA_DIR'], 'images.json')
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump([], f)

    def get_all_images(self):
        with open(self.filename, 'r', encoding='utf-8') as f:
            return json.load(f)

    def add_image(self, image_dict):
        images = self.get_all_images()
        images.append(image_dict)
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(serialize_object(images), f, indent=2, ensure_ascii=False)

# Storage 类，用于项目及笔记管理
class Storage:
    def __init__(self, data_dir=None):
        self.data_dir = data_dir or app.config['DATA_DIR']
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_project_path(self, project_id):
        return os.path.join(self.data_dir, project_id)

    def get_projects(self):
        projects = []
        for dir_name in os.listdir(self.data_dir):
            project_dir = self._get_project_path(dir_name)
            meta_file = os.path.join(project_dir, 'metadata.json')
            if os.path.exists(meta_file):
                with open(meta_file, 'r', encoding='utf-8') as f:
                    project = json.load(f)
                    project['created_at'] = str_to_datetime(project['created_at'])
                    project['updated_at'] = str_to_datetime(project['updated_at'])
                    projects.append(project)
        return sorted(projects, key=lambda x: x['created_at'], reverse=True)

    def create_project(self, name):
        project_id = str(uuid.uuid4())
        project_dir = self._get_project_path(project_id)
        os.makedirs(project_dir, exist_ok=True)
        metadata = {
            'id': project_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'notes': [],
            'images': []
        }
        with open(os.path.join(project_dir, 'metadata.json'), 'w', encoding='utf-8') as f:
            json.dump(serialize_object(metadata), f, ensure_ascii=False, indent=2)
        return metadata

    def get_project(self, project_id):
        project_dir = self._get_project_path(project_id)
        meta_file = os.path.join(project_dir, 'metadata.json')
        if not os.path.exists(meta_file):
            return None
        with open(meta_file, 'r', encoding='utf-8') as f:
            project = json.load(f)
            project['created_at'] = str_to_datetime(project['created_at'])
            project['updated_at'] = str_to_datetime(project['updated_at'])
            project['notes'] = sorted(project['notes'], key=lambda x: x['created_at'], reverse=True)
            for note in project['notes']:
                note['created_at'] = str_to_datetime(note['created_at'])
                note['updated_at'] = str_to_datetime(note['updated_at'])
            return project

    def create_note(self, project_id, title):
        project = self.get_project(project_id)
        if not project:
            return None
        note_id = str(uuid.uuid4())
        note_file = os.path.join(self._get_project_path(project_id), f'{note_id}.md')
        initial_content = "# New Note\nStart writing here..."
        with open(note_file, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        note_meta = {
            'id': note_id,
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'hash': compute_hash(initial_content)
        }
        project['notes'].append(note_meta)
        project['updated_at'] = datetime.now().isoformat()
        self._save_project_meta(project_id, project)
        return note_meta

    def get_note_content(self, project_id, note_id):
        note_file = os.path.join(self._get_project_path(project_id), f'{note_id}.md')
        if not os.path.exists(note_file):
            return None
        with open(note_file, 'r', encoding='utf-8') as f:
            return f.read()

    def update_note(self, project_id, note_id, title, content):
        project = self.get_project(project_id)
        if not project:
            return None
        note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
        if not note_meta:
            return None
        note_file = os.path.join(self._get_project_path(project_id), f'{note_id}.md')
        with open(note_file, 'w', encoding='utf-8') as f:
            f.write(content)
        note_meta['title'] = title
        note_meta['updated_at'] = datetime.now().isoformat()
        note_meta['hash'] = compute_hash(content)
        project['updated_at'] = datetime.now().isoformat()
        self._save_project_meta(project_id, project)
        return note_meta

    def _save_project_meta(self, project_id, metadata):
        meta_file = os.path.join(self._get_project_path(project_id), 'metadata.json')
        with open(meta_file, 'w', encoding='utf-8') as f:
            json.dump(serialize_object(metadata), f, ensure_ascii=False, indent=2)

def render_markdown_with_bootstrap(md_content):
    html = markdown.markdown(md_content, extensions=['extra'])
    container = div(_class="card")
    card_body = div(_class="card-body")
    card_body.add(raw(html))
    container.add(card_body)
    return str(container)

# ---------------------- 基本页面路由 ----------------------
@app.route('/')
def index():
    storage = Storage()
    projects = storage.get_projects()
    return render_template('index.html', projects=projects)

@app.route('/projects/<project_id>')
def project_detail(project_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        abort(404)
    return render_template('project_detail.html', project=project)

@app.route('/projects/<project_id>/notes/<note_id>/edit')
def note_edit(project_id, note_id):
    storage = Storage()
    project = storage.get_project(project_id)
    note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
    if not project or not note_meta:
        abort(404)
    content = storage.get_note_content(project_id, note_id)
    return render_template('note_edit.html', project=project, note={**note_meta, 'content': content})

@app.route('/projects/<project_id>/notes/<note_id>/preview')
def note_preview(project_id, note_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        abort(404)
    note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
    if not note_meta:
        abort(404)
    md_content = storage.get_note_content(project_id, note_id)
    bootstrap_html = render_markdown_with_bootstrap(md_content)
    return render_template('note_preview.html', project=project, note=note_meta, content=bootstrap_html)

# ---------------------- API 接口 ----------------------
# 以下按照 URL 前缀分组

# ----- Project 相关接口 -----
@app.route('/api/projects', methods=['POST'])
def create_project():
    name = request.json.get('name')
    if not name:
        return jsonify({'error': 'Missing name'}), 400
    storage = Storage()
    project = storage.create_project(name)
    return jsonify(serialize_object(project)), 201

@app.route('/api/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    project_dir = storage._get_project_path(project_id)
    shutil.rmtree(project_dir)
    return jsonify({'message': 'Project deleted'}), 200

@app.route('/api/projects/import', methods=['POST'])
def import_project():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
    file.save(temp_file.name)
    temp_file.close()

    storage = Storage()
    new_project_id = str(uuid.uuid4())
    project_dir = storage._get_project_path(new_project_id)
    os.makedirs(project_dir, exist_ok=True)

    try:
        with zipfile.ZipFile(temp_file.name, 'r') as zip_ref:
            zip_ref.extractall(project_dir)
    except Exception as e:
        os.unlink(temp_file.name)
        return jsonify({'error': '解压项目失败', 'details': str(e)}), 400

    os.unlink(temp_file.name)
    metadata_path = os.path.join(project_dir, 'metadata.json')
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            meta = json.load(f)
        meta['id'] = new_project_id
        meta['created_at'] = datetime.now().isoformat()
        meta['updated_at'] = datetime.now().isoformat()
    else:
        shutil.rmtree(project_dir)
        return jsonify({'error': '导入项目失败，未找到 metadata.json'}), 400
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(serialize_object(meta), f, ensure_ascii=False, indent=2)
    return jsonify(meta), 201

@app.route('/api/projects/<project_id>/download_zip', methods=['GET'])
def download_project_zip(project_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        abort(404)
    project_path = storage._get_project_path(project_id)
    temp_dir = tempfile.gettempdir()
    archive_base = os.path.join(temp_dir, project_id)
    archive_path = shutil.make_archive(archive_base, 'zip', root_dir=project_path)
    response = send_file(
        archive_path,
        as_attachment=True,
        download_name=f"{project['name']}.zip",
        mimetype='application/zip'
    )
    @response.call_on_close
    def cleanup():
        if os.path.exists(archive_path):
            os.remove(archive_path)
    return response

# ----- Note 相关接口 -----
@app.route('/api/projects/<project_id>/notes', methods=['POST'])
def create_note(project_id):
    title = request.json.get('title', 'Untitled')
    storage = Storage()
    note_meta = storage.create_note(project_id, title)
    if not note_meta:
        return jsonify({'error': 'Project not found'}), 404
    return jsonify(serialize_object(note_meta)), 201

@app.route('/api/projects/<project_id>/notes/<note_id>', methods=['PUT'])
def update_note(project_id, note_id):
    data = request.json
    title = data.get('title')
    content = data.get('content')
    if not title or not content:
        return jsonify({'error': 'Missing title or content'}), 400
    storage = Storage()
    updated_note = storage.update_note(project_id, note_id, title, content)
    if not updated_note:
        return jsonify({'error': 'Note not found'}), 404
    return jsonify(serialize_object(updated_note)), 200

@app.route('/api/projects/<project_id>/notes/<note_id>', methods=['DELETE'])
def delete_note(project_id, note_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
    if not note_meta:
        return jsonify({'error': 'Note not found'}), 404
    note_file = os.path.join(storage._get_project_path(project_id), f'{note_id}.md')
    if os.path.exists(note_file):
        os.remove(note_file)
    project['notes'] = [n for n in project['notes'] if n['id'] != note_id]
    project['updated_at'] = datetime.now().isoformat()
    storage._save_project_meta(project_id, project)
    return jsonify({'message': 'Note deleted'}), 200

@app.route('/api/projects/<project_id>/notes/<note_id>/move', methods=['PUT'])
def move_note(project_id, note_id):
    data = request.json
    target_project_id = data.get('target_project_id')
    if not target_project_id:
        return jsonify({'error': 'Missing target_project_id'}), 400
    storage = Storage()
    source_project = storage.get_project(project_id)
    target_project = storage.get_project(target_project_id)
    if not source_project or not target_project:
        return jsonify({'error': 'Source or target project not found'}), 404
    note_meta = next((n for n in source_project['notes'] if n['id'] == note_id), None)
    if not note_meta:
        return jsonify({'error': 'Note not found in source project'}), 404
    note_file_source = os.path.join(storage._get_project_path(project_id), f'{note_id}.md')
    if not os.path.exists(note_file_source):
        return jsonify({'error': 'Note file not found'}), 404
    target_project_dir = storage._get_project_path(target_project_id)
    note_file_target = os.path.join(target_project_dir, f'{note_id}.md')
    os.rename(note_file_source, note_file_target)
    source_project['notes'] = [n for n in source_project['notes'] if n['id'] != note_id]
    source_project['updated_at'] = datetime.now().isoformat()
    storage._save_project_meta(project_id, source_project)
    note_meta['updated_at'] = datetime.now().isoformat()
    target_project['notes'].append(note_meta)
    target_project['updated_at'] = datetime.now().isoformat()
    storage._save_project_meta(target_project_id, target_project)
    return jsonify({'message': 'Note moved successfully'}), 200

@app.route('/api/projects/<project_id>/notes/<note_id>/verify', methods=['GET'])
def verify_note_hash(project_id, note_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
    if not note_meta:
        return jsonify({'error': 'Note not found'}), 404
    file_content = storage.get_note_content(project_id, note_id)
    if file_content is None:
        return jsonify({'error': 'Note file not found'}), 404
    current_hash = compute_hash(file_content)
    valid = (current_hash == note_meta.get('hash'))
    return jsonify({'valid': valid, 'stored_hash': note_meta.get('hash'), 'current_hash': current_hash}), 200

@app.route('/api/projects/<project_id>/notes/<note_id>/download', methods=['GET'])
def download_note(project_id, note_id):
    storage = Storage()
    project = storage.get_project(project_id)
    if not project:
        abort(404)
    note_meta = next((n for n in project['notes'] if n['id'] == note_id), None)
    if not note_meta:
        abort(404)
    note_file = os.path.join(storage._get_project_path(project_id), f'{note_id}.md')
    if not os.path.exists(note_file):
        abort(404)
    return send_file(
        note_file,
        as_attachment=True,
        download_name=f"{note_meta['title']}.md",
        mimetype='text/markdown'
    )

# ----- Image 相关接口 -----
@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件部分'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '未选择文件'}), 400

    file_bytes = file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    ext = os.path.splitext(file.filename)[1]
    date_path = datetime.now().strftime("%Y/%m/%d")
    upload_folder = os.path.join(app.root_path, 'static', 'uploads', date_path)
    os.makedirs(upload_folder, exist_ok=True)
    filename = f"{file_hash}{ext}"
    file_path = os.path.join(upload_folder, filename)

    gs = ImageStorage()
    images = gs.get_all_images()
    for img in images:
        if img.get('filename') == filename:
            return jsonify({'url': img['url'], 'md': f"![]({img['url']})"}), 200

    file.seek(0)
    file.save(file_path)
    file_url = url_for('static', filename=f'uploads/{date_path}/{filename}', _external=True)
    image_obj = Image(filename=filename, url=file_url)
    gs.add_image(image_obj.to_dict())
    markdown_text = f"![]({file_url})"
    return jsonify({'url': file_url, 'md': markdown_text}), 200

@app.route('/api/images/<image_id>', methods=['DELETE'])
def delete_image(image_id):
    gs = ImageStorage()
    images = gs.get_all_images()
    image = next((img for img in images if img['id'] == image_id), None)
    if not image:
        return jsonify({'error': '图片未找到'}), 404

    try:
        static_part = image['url'].split('/static/')[1]
        file_path = os.path.join(app.root_path, 'static', static_part)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print(e)

    images = [img for img in images if img['id'] != image_id]
    with open(gs.filename, 'w', encoding='utf-8') as f:
        json.dump(serialize_object(images), f, indent=2, ensure_ascii=False)
    return jsonify({'message': '图片已删除'}), 200

# ----- Gallery 页面 -----
@app.route('/gallery')
def gallery():
    gs = ImageStorage()
    images = gs.get_all_images()
    return render_template('gallery.html', images=images)

# ---------------------- after_request 钩子 ----------------------
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response

if __name__ == '__main__':
    app.run(debug=True)