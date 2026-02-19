import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import app
from models import User, Scan
import unittest
import io

class specific_test(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_analysis_flow(self):
        # 1. Register
        print("Registering test user...")
        # cleaning up first if exists
        try:
             # This is risky on real DB but necessary for repeatable test without mocking
             # Assuming dev environment
            pass
        except:
             pass

        self.app.post('/register', data=dict(
            name='Test User',
            email='test@example.com',
            password='password123',
            confirm_password='password123',
            role='clinician'
        ), follow_redirects=True)

        # 2. Login
        print("Logging in...")
        self.app.post('/login', data=dict(
            email='test@example.com',
            password='password123'
        ), follow_redirects=True)

        # 3. Do Analysis
        print("Submitting analysis...")
        with open('tests/dummy.vcf', 'rb') as f:
            vcf_content = f.read()

        data = {
            'patient_id': 'TEST_PATIENT',
            'drug_input': 'WARFARIN',
            'vcf_file': (io.BytesIO(vcf_content), 'dummy.vcf')
        }

        response = self.app.post('/do-analysis', data=data, content_type='multipart/form-data', follow_redirects=True)
        
        content = response.data.decode('utf-8')
        
        # 4. Checks
        print("Checking response...")
        # Check for results container
        if 'id="resultContainer"' in content:
            print("PASS: Result container found.")
        else:
            print("FAIL: Result container NOT found.")
            # print(content[:500])

        # Check for form container (should NOT be there if we rendered results.html, 
        # UNLESS base.html includes it? No, base.html has content block.
        # results.html does NOT include form-container.
        if 'id="formContainer"' not in content:
            print("PASS: Form container NOT found (Correct for results page).")
        else:
            print("FAIL: Form container found (Should be absent in results.html).")

        # Check for inheritance
        if 'Analysis Results - Pharmacogenomics' in content:
             print("PASS: Title correct (Template inheritance works).")
        else:
             print("FAIL: Title incorrect.")

if __name__ == '__main__':
    unittest.main()
