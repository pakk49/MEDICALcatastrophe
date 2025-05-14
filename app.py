from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json
import plotly
import plotly.graph_objs as go
import pandas as pd
import os

# สร้าง Flask app
app = Flask(__name__)

# ตั้งค่า Secret Key จาก environment variable หรือใช้ค่าเริ่มต้นถ้าไม่มี
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# ตั้งค่าเพิ่มเติมสำหรับ production
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PROPAGATE_EXCEPTIONS'] = True  # เพื่อให้เห็น error details

# ตั้งค่าฐานข้อมูล - ใช้ DATABASE_URL จาก environment variable ถ้ามี
database_url = os.environ.get('DATABASE_URL')

try:
    if database_url:
        # แก้ไข URL สำหรับ PostgreSQL บน Render.com
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 5,
            'max_overflow': 2,
            'pool_timeout': 30,
            'pool_recycle': 1800,
        }
    else:
        # ใช้ SQLite สำหรับ development
        base_dir = os.path.abspath(os.path.dirname(__file__))
        db_path = os.path.join(base_dir, 'instance', 'medical_app.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
except Exception as e:
    print(f"Database configuration error: {e}")

# สร้าง instances
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# ตั้งค่า login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'กรุณาเข้าสู่ระบบก่อนใช้งาน'

# Custom Jinja2 filters
@app.template_filter('fromjson')
def fromjson_filter(value):
    try:
        return json.loads(value)
    except:
        return []

def translate_symptom(symptom_code):
    symptoms_dict = {
        # อาการทั่วไป
        'fever': 'มีไข้',
        'fatigue': 'อ่อนเพลีย',
        'weakness': 'อ่อนแรง',
        'body_ache': 'ปวดเมื่อยตามตัว',
        'night_sweats': 'เหงื่อออกตอนกลางคืน',
        'weight_loss': 'น้ำหนักลด',
        'weight_gain': 'น้ำหนักเพิ่ม',
        'chills': 'หนาวสั่น',
        'poor_appetite': 'เบื่ออาหาร',
        'malaise': 'รู้สึกไม่สบายตัว',

        # ระบบทางเดินหายใจ
        'cough': 'ไอ',
        'shortness_breath': 'หายใจลำบาก',
        'runny_nose': 'น้ำมูกไหล',
        'sneezing': 'จาม',
        'sore_throat': 'เจ็บคอ',
        'nasal_congestion': 'คัดจมูก',
        'chest_pain': 'เจ็บหน้าอก',
        'wheezing': 'หายใจมีเสียงหวีด',
        'rapid_breathing': 'หายใจเร็ว',
        'coughing_blood': 'ไอเป็นเลือด',

        # ระบบทางเดินอาหาร
        'nausea': 'คลื่นไส้',
        'vomiting': 'อาเจียน',
        'diarrhea': 'ท้องเสีย',
        'constipation': 'ท้องผูก',
        'stomach_pain': 'ปวดท้อง',
        'bloating': 'ท้องอืด',
        'heartburn': 'แสบร้อนกลางอก',
        'abdominal_pain': 'ปวดท้องน้อย',
        'bloody_stool': 'อุจจาระมีเลือดปน',
        'excessive_gas': 'มีแก๊สในท้องมาก',

        # ระบบประสาทและสมอง
        'headache': 'ปวดศีรษะ',
        'dizziness': 'วิงเวียน',
        'confusion': 'สับสน',
        'memory_problems': 'ความจำไม่ดี',
        'seizures': 'ชัก',
        'tremors': 'มือสั่น',
        'difficulty_speaking': 'พูดลำบาก',
        'difficulty_walking': 'เดินลำบาก',
        'numbness': 'ชา',
        'tingling': 'รู้สึกเหมือนเข็มทิ่ม',

        # ระบบกล้ามเนื้อและกระดูก
        'joint_pain': 'ปวดข้อ',
        'muscle_pain': 'ปวดกล้ามเนื้อ',
        'back_pain': 'ปวดหลัง',
        'neck_pain': 'ปวดคอ',
        'stiffness': 'ข้อฝืด',
        'swelling': 'บวม',
        'muscle_weakness': 'กล้ามเนื้ออ่อนแรง',
        'muscle_cramps': 'ตะคริว',
        'joint_stiffness': 'ข้อติด',
        'bone_pain': 'ปวดกระดูก',

        # ผิวหนังและเยื่อบุ
        'rash': 'ผื่น',
        'itching': 'คัน',
        'skin_changes': 'ผิวหนังเปลี่ยนแปลง',
        'bruising': 'จ้ำเลือด',
        'dry_skin': 'ผิวแห้ง',
        'excessive_sweating': 'เหงื่อออกมาก',
        'pale_skin': 'ผิวซีด',
        'yellow_skin': 'ผิวเหลือง',
        'skin_pain': 'ผิวหนังเจ็บ',
        'hair_loss': 'ผมร่วง',

        # ตา หู คอ จมูก
        'vision_problems': 'ปัญหาการมองเห็น',
        'hearing_problems': 'ปัญหาการได้ยิน',
        'ear_pain': 'ปวดหู',
        'ringing_ears': 'หูอื้อ',
        'eye_pain': 'ปวดตา',
        'watery_eyes': 'น้ำตาไหล',
        'red_eyes': 'ตาแดง',
        'sinus_pressure': 'แน่นไซนัส',
        'nose_bleeds': 'เลือดกำเดาไหล',
        'hoarseness': 'เสียงแหบ',

        # ระบบหัวใจและหลอดเลือด
        'chest_pain_heart': 'เจ็บหน้าอกจากหัวใจ',
        'palpitations': 'ใจสั่น',
        'irregular_heartbeat': 'หัวใจเต้นผิดจังหวะ',
        'high_blood_pressure': 'ความดันโลหิตสูง',
        'low_blood_pressure': 'ความดันโลหิตต่ำ',
        'swelling_legs': 'ขาบวม',
        'cold_hands_feet': 'มือเท้าเย็น',
        'varicose_veins': 'เส้นเลือดขอด',
        'fainting': 'เป็นลม',
        'bluish_skin': 'ผิวเขียวคล้ำ',

        # อาการเกี่ยวกับการนอน
        'insomnia': 'นอนไม่หลับ',
        'sleep_too_much': 'นอนมากผิดปกติ',
        'sleep_apnea': 'หยุดหายใจขณะนอนหลับ',
        'snoring': 'นอนกรน',
        'nightmares': 'ฝันร้าย',
        'sleepwalking': 'ละเมอเดิน',

        # อาการเกี่ยวกับอารมณ์และจิตใจ
        'anxiety': 'วิตกกังวล',
        'depression': 'ซึมเศร้า',
        'mood_swings': 'อารมณ์แปรปรวน',
        'irritability': 'หงุดหงิดง่าย',
        'panic_attacks': 'อาการตื่นตระหนก',
        'loss_of_interest': 'ไม่สนใจสิ่งรอบตัว',
        'hopelessness': 'รู้สึกสิ้นหวัง',

        # อาการระบบฮอร์โมน
        'thyroid_problems': 'ปัญหาต่อมไทรอยด์',
        'hot_flashes': 'ร้อนวูบวาบ',
        'excessive_thirst': 'กระหายน้ำมาก',
        'frequent_urination': 'ปัสสาวะบ่อย',
        'menstrual_changes': 'ประจำเดือนผิดปกติ',
        'erectile_dysfunction': 'ปัญหาการแข็งตัว',
        'breast_changes': 'การเปลี่ยนแปลงของเต้านม',

        # อาการระบบภูมิคุ้มกัน
        'frequent_infections': 'ติดเชื้อง่าย',
        'slow_healing': 'แผลหายช้า',
        'autoimmune_symptoms': 'อาการภูมิต้านตัวเอง',
        'allergic_reactions': 'อาการแพ้',
        'lymph_node_swelling': 'ต่อมน้ำเหลืองบวม',
        'immune_weakness': 'ภูมิคุ้มกันอ่อนแอ',
        
        # อาการเกี่ยวกับช่องปากและฟัน
        'tooth_pain': 'ปวดฟัน',
        'bleeding_gums': 'เหงือกเลือดออก',
        'mouth_ulcers': 'แผลในปาก',
        'bad_breath': 'กลิ่นปาก',
        'dry_mouth': 'ปากแห้ง',
        'teeth_grinding': 'นอนกัดฟัน',
        'difficulty_swallowing': 'กลืนลำบาก',
    }
    return symptoms_dict.get(symptom_code, symptom_code)

@app.template_filter('translate_symptom')
def translate_symptom_filter(symptom_code):
    return translate_symptom(symptom_code)

def get_diseases():
    diseases = {
        # โรคระบบทางเดินหายใจ
        'common_cold': {
            'name': 'ไข้หวัดธรรมดา',
            'symptoms': ['runny_nose', 'cough', 'sore_throat', 'fever', 'sneezing'],
            'description': 'โรคติดเชื้อทางเดินหายใจส่วนบนที่พบบ่อย อาการมักไม่รุนแรงและหายได้เอง'
        },
        'flu': {
            'name': 'ไข้หวัดใหญ่',
            'symptoms': ['fever', 'body_ache', 'fatigue', 'cough', 'headache'],
            'description': 'โรคติดเชื้อไวรัสที่มีอาการรุนแรงกว่าไข้หวัดธรรมดา มักมีไข้สูงและปวดเมื่อยมาก'
        },
        'bronchitis': {
            'name': 'หลอดลมอักเสบ',
            'symptoms': ['cough', 'chest_pain', 'shortness_breath', 'wheezing', 'fatigue'],
            'description': 'การอักเสบของหลอดลม ทำให้ไอมาก มีเสมหะ และหายใจลำบาก'
        },
        'pneumonia': {
            'name': 'ปอดบวม',
            'symptoms': ['fever', 'cough', 'shortness_breath', 'chest_pain', 'rapid_breathing'],
            'description': 'การติดเชื้อที่ปอด ทำให้มีอาการไข้ ไอ หายใจหอบ และเหนื่อยง่าย'
        },
        'asthma': {
            'name': 'โรคหืด',
            'symptoms': ['wheezing', 'shortness_breath', 'chest_pain', 'cough', 'difficulty_breathing'],
            'description': 'โรคเรื้อรังที่ทำให้หลอดลมตีบแคบ หายใจมีเสียงหวีด และหายใจลำบาก'
        },

        # โรคระบบทางเดินอาหาร
        'gastritis': {
            'name': 'กระเพาะอาหารอักเสบ',
            'symptoms': ['stomach_pain', 'nausea', 'poor_appetite', 'bloating', 'heartburn'],
            'description': 'การอักเสบของกระเพาะอาหาร ทำให้ปวดท้อง จุกเสียด และเบื่ออาหาร'
        },
        'food_poisoning': {
            'name': 'อาหารเป็นพิษ',
            'symptoms': ['nausea', 'vomiting', 'diarrhea', 'stomach_pain', 'fever'],
            'description': 'การติดเชื้อในระบบทางเดินอาหารจากการรับประทานอาหารที่ปนเปื้อนเชื้อโรค'
        },
        'peptic_ulcer': {
            'name': 'แผลในกระเพาะอาหาร',
            'symptoms': ['stomach_pain', 'heartburn', 'nausea', 'poor_appetite', 'weight_loss'],
            'description': 'แผลที่เกิดขึ้นในกระเพาะอาหารหรือลำไส้เล็กส่วนต้น ทำให้ปวดท้องรุนแรง'
        },
        
        # โรคระบบประสาทและสมอง
        'migraine': {
            'name': 'ไมเกรน',
            'symptoms': ['headache', 'nausea', 'vision_problems', 'sensitivity_to_light', 'vomiting'],
            'description': 'อาการปวดศีรษะรุนแรงข้างเดียว มักมีอาการคลื่นไส้และแพ้แสงร่วมด้วย'
        },
        'tension_headache': {
            'name': 'ปวดศีรษะจากความเครียด',
            'symptoms': ['headache', 'neck_pain', 'fatigue', 'difficulty_sleeping', 'irritability'],
            'description': 'อาการปวดศีรษะที่เกิดจากความเครียดและความตึงของกล้ามเนื้อ'
        },

        # โรคระบบกล้ามเนื้อและกระดูก
        'arthritis': {
            'name': 'ข้ออักเสบ',
            'symptoms': ['joint_pain', 'joint_stiffness', 'swelling', 'reduced_mobility', 'morning_stiffness'],
            'description': 'โรคที่ทำให้ข้อต่ออักเสบ บวม และเคลื่อนไหวลำบาก'
        },
        'back_pain': {
            'name': 'อาการปวดหลัง',
            'symptoms': ['back_pain', 'muscle_pain', 'stiffness', 'reduced_mobility', 'numbness'],
            'description': 'อาการปวดที่บริเวณหลัง อาจเกิดจากการบาดเจ็บหรือความผิดปกติของกระดูกสันหลัง'
        },

        # โรคผิวหนัง
        'eczema': {
            'name': 'โรคผื่นภูมิแพ้ผิวหนัง',
            'symptoms': ['itching', 'rash', 'dry_skin', 'skin_changes', 'redness'],
            'description': 'โรคผิวหนังอักเสบเรื้อรัง ทำให้ผิวแห้ง คัน และมีผื่นแดง'
        },
        'psoriasis': {
            'name': 'โรคสะเก็ดเงิน',
            'symptoms': ['skin_changes', 'itching', 'rash', 'joint_pain', 'skin_pain'],
            'description': 'โรคผิวหนังเรื้อรังที่ทำให้เกิดผื่นหนาสีแดงและมีสะเก็ดสีเงิน'
        },

        # โรคระบบหัวใจและหลอดเลือด
        'hypertension': {
            'name': 'ความดันโลหิตสูง',
            'symptoms': ['high_blood_pressure', 'headache', 'dizziness', 'vision_problems', 'chest_pain'],
            'description': 'ภาวะที่ความดันโลหิตสูงกว่าปกติ เพิ่มความเสี่ยงต่อโรคหัวใจและหลอดเลือด'
        },
        'heart_disease': {
            'name': 'โรคหัวใจ',
            'symptoms': ['chest_pain_heart', 'shortness_breath', 'fatigue', 'irregular_heartbeat', 'swelling_legs'],
            'description': 'โรคที่เกี่ยวกับหัวใจและหลอดเลือด อาจเกิดจากหลอดเลือดหัวใจตีบหรือหัวใจทำงานผิดปกติ'
        }
    }
    return diseases

def diagnose(selected_symptoms):
    diseases = get_diseases()
    diagnosis_results = []
    
    # ดึงข้อมูลโรคประจำตัวของผู้ใช้
    user_conditions = current_user.health_conditions.split(',') if current_user.health_conditions else []
    user_allergies = current_user.drug_allergies.split(',') if current_user.drug_allergies else []
    
    for disease_id, disease in diseases.items():
        # คำนวณความเหมือนของอาการ
        matching_symptoms = set(selected_symptoms) & set(disease['symptoms'])
        if matching_symptoms:
            # คำนวณเปอร์เซ็นต์ความเป็นไปได้
            match_percentage = (len(matching_symptoms) / len(disease['symptoms'])) * 100
            
            # เพิ่มน้ำหนักคะแนนถ้าตรงกับโรคประจำตัว
            if disease['name'] in user_conditions:
                match_percentage += 20
            
            if match_percentage >= 30:  # แสดงเฉพาะโรคที่มีความเป็นไปได้มากกว่า 30%
                diagnosis_result = {
                    'disease_id': disease_id,
                    'name': disease['name'],
                    'description': disease['description'],
                    'matching_symptoms': [translate_symptom(s) for s in matching_symptoms],
                    'match_percentage': round(match_percentage, 1)
                }
                
                # เพิ่มคำเตือนถ้าผู้ป่วยมีโรคประจำตัว
                if disease['name'] in user_conditions:
                    diagnosis_result['warning'] = 'คุณมีประวัติเป็นโรคนี้'
                    
                diagnosis_results.append(diagnosis_result)
    
    # เรียงลำดับผลลัพธ์ตามเปอร์เซ็นต์ความเป็นไปได้
    diagnosis_results.sort(key=lambda x: x['match_percentage'], reverse=True)
    return diagnosis_results[:5]  # แสดงเฉพาะ 5 อันดับแรก

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
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # อัพเดตข้อมูลพื้นฐาน
        current_user.email = request.form.get('email')
        current_user.birth_date = datetime.strptime(request.form.get('birth_date'), '%Y-%m-%d')
        current_user.gender = request.form.get('gender')
        
        # อัพเดตข้อมูลสุขภาพ
        current_user.health_conditions = request.form.get('health_conditions')
        current_user.drug_allergies = request.form.get('drug_allergies')

        # ถ้ามีการเปลี่ยนรหัสผ่าน
        new_password = request.form.get('new_password')
        if new_password:
            if current_user.check_password(request.form.get('current_password')):
                current_user.set_password(new_password)
            else:
                flash('รหัสผ่านปัจจุบันไม่ถูกต้อง')
                return redirect(url_for('edit_profile'))

        try:
            db.session.commit()
            flash('อัพเดตข้อมูลสำเร็จ')
            return redirect(url_for('dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('เกิดข้อผิดพลาดในการอัพเดตข้อมูล')
            return redirect(url_for('edit_profile'))

    return render_template('edit_profile.html')

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
        
        # Diagnose
        diagnosis_results = diagnose(symptoms)
        
        # Generate recommendation
        severity = 'low' if len(symptoms) < 3 else 'medium' if len(symptoms) < 5 else 'high'
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
            diagnosis=json.dumps(diagnosis_results),
            recommendation=recommendation
        )
        db.session.add(consultation)
        db.session.commit()        # ดึงข้อมูลการแพ้ยาและโรคประจำตัว
        health_conditions = current_user.health_conditions or "ไม่มี"
        drug_allergies = current_user.drug_allergies or "ไม่มี"
        
        return render_template('results.html', 
                            conditions=diagnosis_results,
                            recommendation=recommendation,
                            bmi=bmi,
                            health_conditions=health_conditions,
                            drug_allergies=drug_allergies)

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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()  # Roll back db session in case of error
    return render_template('500.html'), 500

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"}), 200

def init_db():
    """ฟังก์ชันสำหรับสร้างฐานข้อมูล"""
    try:
        with app.app_context():
            # สร้างตารางถ้ายังไม่มี
            db.create_all()
            print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
        return False
    return True

if __name__ == '__main__':
    try:
        # สร้างฐานข้อมูล
        if not init_db():
            print("Failed to initialize database. Exiting...")
            exit(1)
        
        # รันแอพพลิเคชัน
        app.run(host='127.0.0.1', port=5000, debug=True)
    except Exception as e:
        print(f"Application error: {e}")
        exit(1)
