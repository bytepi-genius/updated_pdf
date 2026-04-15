import os
import io
import zipfile
import traceback
from flask import Flask, request, send_file, render_template, jsonify
from PIL import Image
from PyPDF2 import PdfMerger

app = Flask(__name__)
# Max content length limit optional, e.g., 50MB
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

ALLOWED_EXTENSIONS_IMG = {'png', 'jpg', 'jpeg', 'webp'}
ALLOWED_EXTENSIONS_PDF = {'pdf'}

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/convert/single-image', methods=['POST'])
def single_image():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_IMG):
            img = Image.open(file.stream)
            img = img.convert('RGB')
            
            pdf_bytes = io.BytesIO()
            img.save(pdf_bytes, format='PDF')
            pdf_bytes.seek(0)
            
            out_filename = os.path.splitext(file.filename)[0] + '.pdf'
            
            return send_file(
                pdf_bytes,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=out_filename
            )
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert/multi-image', methods=['POST'])
def multi_image():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
            
        files = request.files.getlist('files[]')
        action = request.form.get('action', 'merge') # 'merge' or 'zip'
        
        if not files or files[0].filename == '':
            return jsonify({'error': 'No selected files'}), 400
            
        images = []
        for file in files:
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_IMG):
                img = Image.open(file.stream)
                img = img.convert('RGB')
                images.append((file.filename, img))
                
        if not images:
            return jsonify({'error': 'No valid images provided'}), 400

        if action == 'merge':
            pdf_bytes = io.BytesIO()
            first_img = images[0][1]
            rest_imgs = [img[1] for img in images[1:]]
            
            first_img.save(
                pdf_bytes, 
                format='PDF', 
                save_all=True, 
                append_images=rest_imgs
            )
            pdf_bytes.seek(0)
            
            return send_file(
                pdf_bytes,
                mimetype='application/pdf',
                as_attachment=True,
                download_name='merged_images.pdf'
            )
            
        elif action == 'zip':
            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, img in images:
                    pdf_bytes = io.BytesIO()
                    img.save(pdf_bytes, format='PDF')
                    pdf_filename = os.path.splitext(filename)[0] + '.pdf'
                    zip_file.writestr(pdf_filename, pdf_bytes.getvalue())
            
            zip_bytes.seek(0)
            return send_file(
                zip_bytes,
                mimetype='application/zip',
                as_attachment=True,
                download_name='converted_pdfs.zip'
            )
        else:
            return jsonify({'error': 'Invalid action'}), 400
            
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert/merge-pdf', methods=['POST'])
def merge_pdf():
    try:
        if 'files[]' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
            
        files = request.files.getlist('files[]')
        if not files or files[0].filename == '':
            return jsonify({'error': 'No selected files'}), 400
            
        merger = PdfMerger()
        
        for file in files:
            if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_PDF):
                merger.append(file.stream)
                
        pdf_bytes = io.BytesIO()
        merger.write(pdf_bytes)
        merger.close()
        pdf_bytes.seek(0)
        
        return send_file(
            pdf_bytes,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='merged_document.pdf'
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
