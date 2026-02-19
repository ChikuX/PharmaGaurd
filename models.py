from pymongo import MongoClient
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from datetime import datetime
from config import Config

client = None
db = None

def init_db(app):
    global client, db
    mongo_uri = app.config.get('MONGO_URI')
    if mongo_uri:
        client = MongoClient(mongo_uri)
        db = client.get_database()
    return db

def get_db():
    return db

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data.get('_id'))
        self.email = user_data.get('email')
        self.name = user_data.get('name', '')
        self.password_hash = user_data.get('password_hash')
        self.role = user_data.get('role', 'clinician')
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self._data = user_data
    
    @staticmethod
    def create(email, password, name='', role='clinician'):
        password_hash = generate_password_hash(password)
        user_doc = {
            'email': email,
            'name': name,
            'password_hash': password_hash,
            'role': role,
            'created_at': datetime.utcnow(),
            'last_login': None
        }
        result = db.users.insert_one(user_doc)
        user_doc['_id'] = result.inserted_id
        return User(user_doc)
    
    @staticmethod
    def get_by_email(email):
        user_data = db.users.find_one({'email': email})
        if user_data:
            return User(user_data)
        return None
    
    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = db.users.find_one({'_id': ObjectId(user_id)})
            if user_data:
                return User(user_data)
        except:
            pass
        return None
    
    @staticmethod
    def update_last_login(user_id):
        try:
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'last_login': datetime.utcnow()}}
            )
        except:
            pass
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Scan:
    @staticmethod
    def create(user_id, patient_id, drug, result_json):
        risk_label = 'Unknown'
        severity = 'none'
        confidence_score = 0.0
        primary_gene = ''
        phenotype = 'Unknown'
        
        if 'risk_assessment' in result_json:
            risk_label = result_json.get('risk_assessment', {}).get('risk_label', 'Unknown')
            severity = result_json.get('risk_assessment', {}).get('severity', 'none')
            confidence_score = result_json.get('risk_assessment', {}).get('confidence_score', 0.0)
        elif 'drug_results' in result_json:
            results = result_json.get('drug_results', [])
            if results:
                risk_label = results[0].get('risk_label', 'Unknown')
                severity = results[0].get('severity', 'none')
                confidence_score = results[0].get('confidence', 0.0)
        
        pgx_profile = result_json.get('pharmacogenomic_profile', {})
        primary_gene = pgx_profile.get('primary_gene', '')
        phenotype = pgx_profile.get('phenotype', 'Unknown')
        
        scan_doc = {
            'user_id': user_id,
            'patient_id': patient_id,
            'drugs': drug,
            'result_json': result_json,
            'overall_risk_label': risk_label,
            'severity': severity,
            'confidence_score': confidence_score,
            'primary_gene': primary_gene,
            'phenotype': phenotype,
            'created_at': datetime.utcnow()
        }
        result = db.scans.insert_one(scan_doc)
        return str(result.inserted_id)
    
    @staticmethod
    def get_by_user(user_id, limit=None, skip=0):
        query = {'user_id': user_id}
        cursor = db.scans.find(query).sort('created_at', -1)
        if limit:
            cursor = cursor.skip(skip).limit(limit)
        return list(cursor)
    
    @staticmethod
    def get_by_id(scan_id, user_id):
        try:
            return db.scans.find_one({'_id': ObjectId(scan_id), 'user_id': user_id})
        except:
            return None
    
    @staticmethod
    def count_by_user(user_id):
        return db.scans.count_documents({'user_id': user_id})
    
    @staticmethod
    def search(user_id, patient_filter='', risk_filter='', drug_filter=''):
        query = {'user_id': user_id}
        
        if patient_filter:
            query['patient_id'] = {'$regex': patient_filter, '$options': 'i'}
        
        if risk_filter:
            query['overall_risk_label'] = risk_filter
        
        if drug_filter:
            query['drugs'] = {'$regex': drug_filter, '$options': 'i'}
        
        return list(db.scans.find(query).sort('created_at', -1))
    
    @staticmethod
    def get_risk_label(result_json):
        if 'risk_assessment' in result_json:
            return result_json.get('risk_assessment', {}).get('risk_label', 'Unknown')
        elif 'drug_results' in result_json:
            results = result_json.get('drug_results', [])
            if results:
                return results[0].get('risk_label', 'Unknown')
        return 'Unknown'
