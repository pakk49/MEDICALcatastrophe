from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import plotly
import plotly.graph_objs as go
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medical_app.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Custom Jinja2 filters
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except:
        return []

def translate_symptom(symptom_code):
    symptoms_dict = {
        'fever': 'มีไข้',
        'fatigue': 'อ่อนเพลีย',
        'weakness': 'อ่อนแรง',
        'body_ache': 'ปวดเมื่อยตามตัว',
        'cough': 'ไอ',
        'shortness_breath': 'หายใจลำบาก',
        'runny_nose': 'น้ำมูกไหล',
        'sneezing': 'จาม',
        'nausea': 'คลื่นไส้',
        'vomiting': 'อาเจียน',
        'diarrhea': 'ท้องเสีย',
        'stomach_pain': 'ปวดท้อง',
        'headache': 'ปวดศีรษะ',
        'sore_throat': 'เจ็บคอ',
        'joint_pain': 'ปวดข้อ',
        'muscle_pain': 'ปวดกล้ามเนื้อ',
        'dizziness': 'วิงเวียน',
        'rash': 'ผื่นคัน'
    }
    return symptoms_dict.get(symptom_code, symptom_code)

@app.template_filter('translate_symptom')
def translate_symptom_filter(symptom_code):
    return translate_symptom(symptom_code)

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    national_id = db.Column(db.String(13), unique=True, nullable=False)
    birth_date = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    health_conditions = db.Column(db.Text, nullable=True)
    drug_allergies = db.Column(db.Text, nullable=True)
    consultations = db.relationship('Consultation', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Consultation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    symptoms = db.Column(db.Text, nullable=False)
    weight = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, nullable=False)
    diagnosis = db.Column(db.Text, nullable=False)
    recommendation = db.Column(db.Text, nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    health_tips = [
        "ดื่มน้ำให้ได้อย่างน้อย 8 แก้วต่อวัน",
        "นอนหลับพักผ่อนให้ได้ 7-9 ชั่วโมงต่อคืน",
        "ออกกำลังกายเป็นประจำ อย่างน้อยวันละ 30 นาที",
        "รับประทานอาหารที่มีประโยชน์ เน้นผักและผลไม้",
        "จัดการความเครียดด้วยการทำสมาธิหรือโยคะ",
        "ตรวจสุขภาพเป็นประจำ",
        "รักษาสุขอนามัย ล้างมือให้สะอาด",
        "ลดอาหารแปรรูปและเครื่องดื่มที่มีน้ำตาล"
    ]
    return render_template('index.html', health_tips=health_tips)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        national_id = request.form.get('national_id')
        birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d')
        gender = request.form.get('gender')
        health_conditions = request.form.get('health_conditions')
        drug_allergies = request.form.get('drug_allergies')

        if User.query.filter_by(username=username).first():
            flash('ชื่อผู้ใช้นี้มีอยู่แล้ว')
            return redirect(url_for('register'))

        if User.query.filter_by(email=email).first():
            flash('อีเมลนี้ได้ลงทะเบียนแล้ว')
            return redirect(url_for('register'))

        user = User(
            username=username, 
            email=email, 
            national_id=national_id,
            birth_date=birth_date, 
            gender=gender,
            health_conditions=health_conditions,
            drug_allergies=drug_allergies
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('ลงทะเบียนสำเร็จ')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and user.check_password(request.form.get('password')):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    consultations = Consultation.query.filter_by(user_id=current_user.id).order_by(Consultation.date.desc()).all()
    
    graphs = {}
    if consultations:
        dates = [c.date for c in consultations]
        
        # BMI Graph
        bmis = [(c.weight / ((c.height/100) ** 2)) for c in consultations]
        bmi_fig = go.Figure(data=[go.Scatter(x=dates, y=bmis, mode='lines+markers', name='BMI')])
        bmi_fig.update_layout(
            title='ประวัติค่าดัชนีมวลกาย (BMI)',
            xaxis_title='วันที่',
            yaxis_title='BMI',
            template='plotly_dark'
        )
        
        # Weight History Graph
        weights = [c.weight for c in consultations]
        weight_fig = go.Figure(data=[go.Scatter(x=dates, y=weights, mode='lines+markers', name='น้ำหนัก')])
        weight_fig.update_layout(
            title='ประวัติน้ำหนัก',
            xaxis_title='วันที่',
            yaxis_title='น้ำหนัก (กก.)',
            template='plotly_dark'
        )
        
        # Symptom Frequency Graph
        all_symptoms = []
        for c in consultations:
            all_symptoms.extend(json.loads(c.symptoms))
        
        symptom_counts = pd.Series(all_symptoms).value_counts()
        symptom_fig = go.Figure(data=[go.Bar(
            x=symptom_counts.index,
            y=symptom_counts.values,
            name='ความถี่อาการ'
        )])
        symptom_fig.update_layout(
            title='ความถี่ของอาการ',
            xaxis_title='อาการ',
            yaxis_title='จำนวนครั้ง',
            template='plotly_dark'
        )
        
        graphs = {
            'bmi': json.dumps(bmi_fig, cls=plotly.utils.PlotlyJSONEncoder),
            'weight': json.dumps(weight_fig, cls=plotly.utils.PlotlyJSONEncoder),
            'symptoms': json.dumps(symptom_fig, cls=plotly.utils.PlotlyJSONEncoder)
        }

    return render_template('dashboard.html', consultations=consultations, graphs=graphs)

@app.route('/symptom_checker', methods=['GET', 'POST'])
@login_required
def symptom_checker():
    if request.method == 'POST':
        symptoms = request.form.getlist('symptoms')
        weight = float(request.form.get('weight'))
        height = float(request.form.get('height'))
        
        # Calculate BMI
        bmi = weight / ((height/100) ** 2)
        
        # Simple symptom analysis (This would be replaced with a more sophisticated system)
        symptom_count = len(symptoms)
        severity = 'low' if symptom_count < 3 else 'medium' if symptom_count < 5 else 'high'
        
        # Mock diagnosis (In reality, this would be much more sophisticated)
        possible_conditions = [
            {"condition": "ไข้หวัดธรรมดา", "probability": 0.8 if "fever" in symptoms and "cough" in symptoms else 0.2},
            {"condition": "ภูมิแพ้", "probability": 0.7 if "runny_nose" in symptoms and "sneezing" in symptoms else 0.1},
            {"condition": "ไข้หวัดใหญ่", "probability": 0.9 if "fever" in symptoms and "body_ache" in symptoms else 0.3}
        ]
        
        # Sort by probability
        possible_conditions.sort(key=lambda x: x["probability"], reverse=True)
        top_conditions = possible_conditions[:3]
        
        # Generate recommendation
        if severity == 'high':
            recommendation = "จากอาการของคุณ แนะนำให้พบแพทย์โดยด่วน"
        elif severity == 'medium':
            recommendation = "ควรเฝ้าระวังอาการ และพบแพทย์หากอาการแย่ลง"
        else:
            recommendation = "พักผ่อนและดูแลตัวเองที่บ้าน พร้อมสังเกตอาการ"

        # Save consultation
        consultation = Consultation(
            user_id=current_user.id,
            symptoms=json.dumps(symptoms),
            weight=weight,
            height=height,
            diagnosis=json.dumps(top_conditions),
            recommendation=recommendation
        )
        db.session.add(consultation)
        db.session.commit()

        return render_template('results.html', 
                            conditions=top_conditions,
                            recommendation=recommendation,
                            bmi=bmi)

    return render_template('symptom_checker.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            # In a real application, send password reset email
            flash('ส่งคำแนะนำการรีเซ็ตรหัสผ่านไปยังอีเมลของคุณแล้ว')
            return redirect(url_for('login'))
        flash('ไม่พบอีเมลนี้ในระบบ')
    return render_template('forgot_password.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
