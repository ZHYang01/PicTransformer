import os
import uuid
import io
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import pillow_heif
from pypdf import PdfWriter

pillow_heif.register_heif_opener()

app = Flask(__name__)
app.secret_key = os.urandom(24)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
CONVERTED_FOLDER = os.path.join(os.path.dirname(__file__), 'converted')
PDF_FOLDER = os.path.join(os.path.dirname(__file__), 'pdf_merged')
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB request cap
MAX_FILES_PER_REQUEST = 30
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'gif', 'tiff', 'webp', 'tif', 'heic', 'heif', 'svg', 'ico', 'psd', 'raw', 'avif', 'pdf'}
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER, PDF_FOLDER]:
    os.makedirs(folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def redirect_to_section(section_id):
    return redirect(f"{url_for('index')}#{section_id}")

def convert_to_jpeg(input_path, output_path, quality=95):
    """Convert any image format to JPEG."""
    with Image.open(input_path) as img:
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        img.save(output_path, 'JPEG', quality=quality)
        original_size = os.path.getsize(input_path)
        converted_size = os.path.getsize(output_path)
        return original_size, converted_size

@app.route('/')
def index():
    return render_template('index.html')

@app.errorhandler(413)
def handle_large_upload(_error):
    flash(f'Upload too large. Maximum request size is {MAX_CONTENT_LENGTH // (1024 * 1024)} MB.')
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files' not in request.files:
        flash('No files provided')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        flash('No files selected')
        return redirect(url_for('index'))
    if len(files) > MAX_FILES_PER_REQUEST:
        flash(f'Too many files. Maximum is {MAX_FILES_PER_REQUEST} per request.')
        return redirect(url_for('index'))
    
    converted_files = []
    session_id = str(uuid.uuid4())
    used_output_names = set()
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            input_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
            file.save(input_path)
            
            base_name = os.path.splitext(filename)[0]
            output_filename = f"{base_name}.jpg"
            suffix = 1
            while output_filename in used_output_names:
                output_filename = f"{base_name}_{suffix}.jpg"
                suffix += 1
            used_output_names.add(output_filename)
            output_path = os.path.join(CONVERTED_FOLDER, f"{session_id}_{output_filename}")
            
            quality = int(request.form.get('quality', 95))
            
            try:
                original_size, converted_size = convert_to_jpeg(input_path, output_path, quality=quality)
                converted_files.append({
                    'original': filename,
                    'converted': output_filename,
                    'session_id': session_id,
                    'original_size': original_size,
                    'converted_size': converted_size
                })
            except Exception as e:
                flash(f'Error converting {filename}: {str(e)}')
            finally:
                if os.path.exists(input_path):
                    os.remove(input_path)
    
    if not converted_files:
        flash('No valid images to convert')
        return redirect(url_for('index'))
    
    return render_template('result.html', files=converted_files, session_id=session_id)

@app.route('/download/<filename>')
def download_file(filename):
    filepath = os.path.join(CONVERTED_FOLDER, filename)
    if not os.path.exists(filepath):
        flash('File not found')
        return redirect(url_for('index'))
    return send_file(filepath, as_attachment=True)

@app.route('/download-all')
def download_all():
    session_id = request.args.get('session_id')
    if not session_id:
        flash('No session found')
        return redirect(url_for('index'))
    
    import zipfile
    import io
    
    session_files = [f for f in os.listdir(CONVERTED_FOLDER) if f.startswith(session_id)]
    if not session_files:
        flash('No files found')
        return redirect(url_for('index'))
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for filename in session_files:
            filepath = os.path.join(CONVERTED_FOLDER, filename)
            arcname = filename.replace(f"{session_id}_", "")
            zipf.write(filepath, arcname)
    
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype='application/zip', 
                   as_attachment=True, download_name='converted_images.zip')

@app.route('/cleanup')
def cleanup():
    import shutil
    session_id = request.args.get('session_id')
    if session_id:
        for folder in [UPLOAD_FOLDER, CONVERTED_FOLDER]:
            for f in os.listdir(folder):
                if f.startswith(session_id):
                    os.remove(os.path.join(folder, f))
    return '', 204

@app.route('/merge-pdf', methods=['POST'])
def merge_pdf():
    if 'files' not in request.files:
        flash('No files provided')
        return redirect_to_section('pdfmerger')
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        flash('No files selected')
        return redirect_to_section('pdfmerger')
    if len(files) > MAX_FILES_PER_REQUEST:
        flash(f'Too many files. Maximum is {MAX_FILES_PER_REQUEST} per request.')
        return redirect_to_section('pdfmerger')
    
    session_id = str(uuid.uuid4())
    saved_files = []
    
    for file in files:
        if file and file.filename and file.filename.lower().endswith('.pdf'):
            filename = secure_filename(file.filename)
            filepath = os.path.join(PDF_FOLDER, f"{session_id}_{filename}")
            file.save(filepath)
            saved_files.append(filepath)
    
    if len(saved_files) < 2:
        for f in saved_files:
            os.remove(f)
        flash('Need at least 2 PDF files to merge')
        return redirect_to_section('pdfmerger')
    
    output_filename = f"merged_{session_id[:8]}.pdf"
    output_path = os.path.join(PDF_FOLDER, output_filename)
    
    try:
        writer = PdfWriter()
        total_original_size = 0
        for pdf_path in saved_files:
            total_original_size += os.path.getsize(pdf_path)
            writer.append(pdf_path)
            os.remove(pdf_path)
        
        with open(output_path, 'wb') as output:
            writer.write(output)
        
        merged_size = os.path.getsize(output_path)
        
        return render_template('pdf_result.html', 
                             merged_file=output_filename,
                             merged_size=merged_size,
                             file_count=len(saved_files))
    except Exception as e:
        flash(f'Error merging PDFs: {str(e)}')
        return redirect(url_for('index'))

@app.route('/download-pdf/<filename>')
def download_pdf(filename):
    filepath = os.path.join(PDF_FOLDER, filename)
    if not os.path.exists(filepath):
        flash('File not found')
        return redirect(url_for('index'))
    return send_file(filepath, as_attachment=True)

@app.route('/image-to-pdf', methods=['POST'])
def image_to_pdf():
    if 'files' not in request.files:
        flash('No files provided')
        return redirect(url_for('index'))
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        flash('No files selected')
        return redirect_to_section('img2pdf')
    if len(files) > MAX_FILES_PER_REQUEST:
        flash(f'Too many files. Maximum is {MAX_FILES_PER_REQUEST} per request.')
        return redirect_to_section('img2pdf')
    
    session_id = str(uuid.uuid4())
    saved_files = []
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
            file.save(filepath)
            saved_files.append(filepath)
    
    if not saved_files:
        flash('No valid images to convert')
        return redirect_to_section('img2pdf')
    
    output_filename = f"images_{session_id[:8]}.pdf"
    output_path = os.path.join(PDF_FOLDER, output_filename)
    
    try:
        writer = PdfWriter()
        total_original_size = 0
        for img_path in saved_files:
            total_original_size += os.path.getsize(img_path)
            with Image.open(img_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                img_buffer = io.BytesIO()
                img.save(img_buffer, format='JPEG')
                img_buffer.seek(0)
                writer.add_image(img_buffer)
            os.remove(img_path)
        
        with open(output_path, 'wb') as output:
            writer.write(output)
        
        merged_size = os.path.getsize(output_path)
        
        return render_template('pdf_result.html', 
                             merged_file=output_filename,
                             merged_size=merged_size,
                             file_count=len(saved_files))
    except Exception as e:
        flash(f'Error converting images to PDF: {str(e)}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=False, port=5000)
