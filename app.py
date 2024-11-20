from flask import Flask, render_template, request, jsonify, url_for, send_file, send_from_directory, jsonify
from zipfile import ZipFile
from io import BytesIO
import os
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


app = Flask(__name__)
app.config['TEMPLATES_FOLDER'] = 'static/templates/'
app.config['DOWNLOAD_FOLDER'] = 'static/downloads/'
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

app.config['MAIL_USERNAME'] = 'azisrosyid.2022@student.uny.ac.id'
app.config['MAIL_PASSWORD'] = 'atli qtoe ceai lwua' 
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False

class TemplateProfile:
    def __init__(self, x, y, font_size, font_color, font_family):
        self.x_percent = x
        self.y_percent = y
        self.font_size = font_size
        self.font_color = font_color
        self.font_family = font_family

template_profiles = [
    TemplateProfile(50, 50, 70, '#000000', 'Arial'),
    TemplateProfile(50, 54, 70, '#000000', 'Arial'),
    TemplateProfile(50, 56, 70, '#000000', 'Arial'),
    TemplateProfile(50, 48, 70, '#000000', 'Arial'),
]

template_profiles_dict = [
    {
        "x_percent": profile.x_percent,
        "y_percent": profile.y_percent,
        "font_size": profile.font_size,
        "font_color": profile.font_color,
        "font_family": profile.font_family
    }
    for profile in template_profiles
]

@app.route('/', methods=['GET', 'POST'])
def index():
    templates = os.listdir(app.config['TEMPLATES_FOLDER'])
    templates = [template for template in templates if template.endswith('.png')] 
    default_template = templates[0] if templates else None 
    
    return render_template('index.html', templates=templates, default_template=default_template, template_profiles=template_profiles_dict)


@app.route('/template/<int:index>', methods=['GET'])
def template(index):
    templates = os.listdir(app.config['TEMPLATES_FOLDER'])
    templates = [template for template in templates if template.endswith('.png')]

    if 0 <= index < len(templates):
        selected_template = templates[index]
    else:
        return "Template not found", 404

    # Return the image file
    return send_from_directory(app.config['TEMPLATES_FOLDER'], selected_template)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'status': 'fail', 'message': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'status': 'fail', 'message': 'No selected file'})

    template_index = int(request.form.get('templateIndex', 0))

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(file_path)

    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return jsonify({'status': 'fail', 'message': f'Failed to read CSV: {e}'})

    if 'name' not in df.columns or 'email' not in df.columns:
        return jsonify({'status': 'fail', 'message': 'CSV format error: columns "name" and "email" required.'})

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, 'w') as zip_file:
        for index, row in df.iterrows():
            name = row['name']
            email = row['email']

            cert_buffer = generate_certificate(name, template_index)
            
            send_certificate_via_email(name, email, cert_buffer)

            zip_file.writestr(f'{name}_certificate.png', cert_buffer.getvalue())
    
    zip_buffer.seek(0)

    return send_file(zip_buffer, mimetype='application/zip', as_attachment=True, download_name='certificates.zip')

def generate_certificate(name, index):
    """
    Generates a certificate for the given name with the selected template.
    Returns the image data as a BytesIO object (in-memory buffer).
    """
    
    template_profile = template_profiles[index]
    
    templates = os.listdir(app.config['TEMPLATES_FOLDER'])
    template_path = os.path.join(app.config['TEMPLATES_FOLDER'], templates[index])
    
    img = Image.open(template_path)

    draw = ImageDraw.Draw(img)
    
    font = ImageFont.truetype('arial.ttf', size=70)
    text_color = (0, 0, 0)

    text_position = (img.width * template_profile.x_percent // 100, img.height * template_profile.y_percent // 100)

    draw.text(text_position, name, font=font, fill=text_color, anchor="mm")

    cert_buffer = BytesIO()
    img.save(cert_buffer, format='PNG')
    cert_buffer.seek(0)

    return cert_buffer

def send_certificate_via_email(name, email, certificate_buffer):
    """
    Sends the generated certificate to the given email address via Gmail SMTP.
    """
    try:
        message = MIMEMultipart()
        message['From'] = app.config['MAIL_USERNAME']
        message['To'] = email
        message['Subject'] = 'Your Webinar Certificate'

        body = f"Hello {name},\n\nPlease find attached your certificate for attending the webinar."
        message.attach(MIMEText(body, 'plain'))

        certificate_buffer.seek(0)
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(certificate_buffer.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={name}_certificate.png')
        message.attach(part)

        with smtplib.SMTP_SSL(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.sendmail(app.config['MAIL_USERNAME'], email, message.as_string())

        print(f'Email sent to {email}')
    except Exception as e:
        print(f'Failed to send email to {email}: {e}')

if __name__ == '__main__':
    os.makedirs(app.config['DOWNLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
