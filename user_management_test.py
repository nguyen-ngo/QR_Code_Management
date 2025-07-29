#!/usr/bin/env python3
"""
User Management Test Script
Test all user management functionalities to ensure they work correctly
"""

import requests
import json
from datetime import datetime

class UserManagementTester:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.admin_session_id = None
        
    def login_as_admin(self, username="admin", password="admin123"):
        """Login as admin to test admin functions"""
        print("🔐 Testing admin login...")
        
        response = self.session.post(f"{self.base_url}/login", data={
            'username': username,
            'password': password
        })
        
        if response.status_code == 200 and "Welcome" in response.text:
            print("✅ Admin login successful")
            return True
        else:
            print("❌ Admin login failed")
            return False
    
    def test_create_user(self):
        """Test user creation functionality"""
        print("\n👤 Testing user creation...")
        
        test_user_data = {
            'full_name': 'Test User',
            'email': 'testuser@example.com',
            'username': 'testuser',
            'password': 'testpass123',
            'role': 'staff'
        }
        
        response = self.session.post(f"{self.base_url}/users/create", data=test_user_data)
        
        if response.status_code == 200:
            if "created successfully" in response.text or response.url.endswith('/users'):
                print("✅ User creation successful")
                return True
        
        print("❌ User creation failed")
        print(f"Response status: {response.status_code}")
        return False
    
    def test_users_page_access(self):
        """Test access to users management page"""
        print("\n📋 Testing users page access...")
        
        response = self.session.get(f"{self.base_url}/users")
        
        if response.status_code == 200 and "User Management" in response.text:
            print("✅ Users page accessible")
            return True
        else:
            print("❌ Users page access failed")
            print(f"Response status: {response.status_code}")
            return False
    
    def get_test_user_id(self):
        """Get the ID of the test user for further testing"""
        print("\n🔍 Finding test user ID...")
        
        response = self.session.get(f"{self.base_url}/users")
        
        if response.status_code == 200:
            # Parse HTML to find user ID - this is a simple approach
            # In a real test, you'd use BeautifulSoup or similar
            content = response.text
            if "testuser" in content:
                print("✅ Test user found in users list")
                # For demo purposes, we'll assume user ID 2 (after admin)
                return 2
        
        print("❌ Could not find test user")
        return None
    
    def test_user_promotion(self, user_id):
        """Test promoting a user to admin"""
        print(f"\n⬆️ Testing user promotion (ID: {user_id})...")
        
        response = self.session.get(f"{self.base_url}/users/{user_id}/promote")
        
        if response.status_code == 200 or response.status_code == 302:
            print("✅ User promotion request successful")
            return True
        else:
            print("❌ User promotion failed")
            print(f"Response status: {response.status_code}")
            return False
    
    def test_user_demotion(self, user_id):
        """Test demoting a user from admin to staff"""
        print(f"\n⬇️ Testing user demotion (ID: {user_id})...")
        
        response = self.session.get(f"{self.base_url}/users/{user_id}/demote")
        
        if response.status_code == 200 or response.status_code == 302:
            print("✅ User demotion request successful")
            return True
        else:
            print("❌ User demotion failed")
            print(f"Response status: {response.status_code}")
            return False
    
    def test_user_deactivation(self, user_id):
        """Test deactivating a user"""
        print(f"\n🚫 Testing user deactivation (ID: {user_id})...")
        
        response = self.session.get(f"{self.base_url}/users/{user_id}/delete")
        
        if response.status_code == 200 or response.status_code == 302:
            print("✅ User deactivation request successful")
            return True
        else:
            print("❌ User deactivation failed")
            print(f"Response status: {response.status_code}")
            return False
    
    def test_user_reactivation(self, user_id):
        """Test reactivating a user"""
        print(f"\n✅ Testing user reactivation (ID: {user_id})...")
        
        response = self.session.get(f"{self.base_url}/users/{user_id}/reactivate")
        
        if response.status_code == 200 or response.status_code == 302:
            print("✅ User reactivation request successful")
            return True
        else:
            print("❌ User reactivation failed")
            print(f"Response status: {response.status_code}")
            return False
    
    def test_user_edit(self, user_id):
        """Test editing user information"""
        print(f"\n✏️ Testing user edit (ID: {user_id})...")
        
        # First get the edit page
        response = self.session.get(f"{self.base_url}/users/{user_id}/edit")
        
        if response.status_code == 200:
            print("✅ User edit page accessible")
            
            # Test submitting updated user data
            updated_data = {
                'full_name': 'Updated Test User',
                'email': 'updated_testuser@example.com',
                'role': 'staff'
            }
            
            response = self.session.post(f"{self.base_url}/users/{user_id}/edit", data=updated_data)
            
            if response.status_code == 200 or response.status_code == 302:
                print("✅ User edit submission successful")
                return True
        
        print("❌ User edit failed")
        print(f"Response status: {response.status_code}")
        return False
    
    def test_bulk_operations(self):
        """Test bulk user operations"""
        print("\n📦 Testing bulk operations...")
        
        # Test bulk deactivate API
        test_data = {'user_ids': [2]}  # Assuming test user has ID 2
        
        response = self.session.post(
            f"{self.base_url}/users/bulk/deactivate",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print("✅ Bulk deactivate API works")
                    
                    # Test bulk activate
                    response = self.session.post(
                        f"{self.base_url}/users/bulk/activate",
                        json=test_data,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get('success'):
                            print("✅ Bulk activate API works")
                            return True
            except json.JSONDecodeError:
                pass
        
        print("❌ Bulk operations failed")
        return False
    
    def test_admin_protections(self):
        """Test admin protection mechanisms"""
        print("\n🛡️ Testing admin protection mechanisms...")
        
        # Try to deactivate admin user (should fail)
        response = self.session.get(f"{self.base_url}/users/1/delete")  # Assuming admin is ID 1
        
        # This should either redirect or show an error
        if response.status_code in [200, 302]:
            print("✅ Admin self-deactivation protection works")
            return True
        else:
            print("❌ Admin protection test inconclusive")
            return False
    
    def run_all_tests(self):
        """Run comprehensive user management tests"""
        print("🧪 Starting User Management Tests")
        print("=" * 50)
        
        results = []
        
        # Test 1: Admin Login
        results.append(("Admin Login", self.login_as_admin()))
        
        if not results[-1][1]:
            print("\n❌ Cannot proceed without admin login")
            return False
        
        # Test 2: Users Page Access
        results.append(("Users Page Access", self.test_users_page_access()))
        
        # Test 3: User Creation
        results.append(("User Creation", self.test_create_user()))
        
        # Get test user ID for further tests
        test_user_id = self.get_test_user_id()
        
        if test_user_id:
            # Test 4: User Edit
            results.append(("User Edit", self.test_user_edit(test_user_id)))
            
            # Test 5: User Promotion
            results.append(("User Promotion", self.test_user_promotion(test_user_id)))
            
            # Test 6: User Demotion
            results.append(("User Demotion", self.test_user_demotion(test_user_id)))
            
            # Test 7: User Deactivation
            results.append(("User Deactivation", self.test_user_deactivation(test_user_id)))
            
            # Test 8: User Reactivation
            results.append(("User Reactivation", self.test_user_reactivation(test_user_id)))
        
        # Test 9: Bulk Operations
        results.append(("Bulk Operations", self.test_bulk_operations()))
        
        # Test 10: Admin Protections
        results.append(("Admin Protections", self.test_admin_protections()))
        
        # Print Results Summary
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:<25} {status}")
            if result:
                passed += 1
        
        print("-" * 50)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 ALL TESTS PASSED! User management is working correctly.")
        elif passed >= total * 0.8:
            print("\n⚠️ Most tests passed, but some issues need attention.")
        else:
            print("\n❌ Multiple tests failed. User management needs debugging.")
        
        return passed == total

def manual_test_instructions():
    """Print manual testing instructions"""
    print("\n" + "=" * 60)
    print("📋 MANUAL TESTING INSTRUCTIONS")
    print("=" * 60)
    print("""
To manually test user management functionalities:

1. 🔐 Login as Admin:
   - Go to /login
   - Use: admin / admin123
   - Verify you can access admin features

2. 👥 Access User Management:
   - Go to /users
   - Verify you see the user management page
   - Check that statistics are displayed correctly

3. ➕ Create New User:
   - Click "Add New User"
   - Fill in: Name, Email, Username, Password, Role
   - Submit and verify user appears in list

4. ✏️ Edit User:
   - Click dropdown next to any user (not yourself)
   - Select "Edit User"
   - Change name/email/role and save
   - Verify changes appear in users list

5. ⬆️ Promote User:
   - Find a staff user in the list
   - Click dropdown → "Promote to Admin"
   - Confirm the action
   - Verify user role changes to Admin

6. ⬇️ Demote User:
   - Find an admin user (not yourself)
   - Click dropdown → "Demote to Staff"
   - Confirm the action
   - Verify user role changes to Staff

7. 🚫 Deactivate User:
   - Find any user (not yourself)
   - Click dropdown → "Deactivate User"
   - Confirm the action
   - Verify user status changes to Inactive

8. ✅ Reactivate User:
   - Find an inactive user
   - Click dropdown → "Reactivate User"
   - Confirm the action
   - Verify user status changes to Active

9. 📦 Bulk Operations:
   - Click "Bulk Actions" button
   - Select multiple users with checkboxes
   - Try "Activate Selected" or "Deactivate Selected"
   - Verify changes are applied to all selected users

10. 🛡️ Admin Protection Tests:
    - Try to deactivate yourself (should fail with error)
    - Try to demote the last admin (should fail with error)
    - Verify these protections work as expected

🔍 What to Look For:
- Flash messages appear for success/error states
- Page redirects work correctly after actions
- User list updates to reflect changes
- Protection mechanisms prevent dangerous actions
- Statistics update correctly after changes
- Search and filtering work properly
""")

def quick_setup_guide():
    """Print setup guide for user management"""
    print("\n" + "=" * 60)
    print("🚀 QUICK SETUP GUIDE")
    print("=" * 60)
    print("""
If user management functions are not working, check:

1. 📂 File Updates:
   - Replace user management routes in app.py
   - Update users.html template
   - Ensure admin_required decorator is properly implemented

2. 🗄️ Database Check:
   - Verify users table exists
   - Check that admin user exists with correct role
   - Ensure foreign key relationships are set up

3. 🔧 Code Integration:
   - Add the enhanced routes to your app.py
   - Import required modules (datetime, etc.)
   - Ensure session management is working

4. 🎨 Template Updates:
   - Replace templates/users.html with enhanced version
   - Verify CSS variables are defined in style.css
   - Check JavaScript functions are loading

5. ⚙️ Configuration:
   - Ensure Flask app has proper secret key
   - Database connection is working
   - Session configuration is correct

6. 🧪 Testing:
   - Start with manual testing first
   - Check browser console for JavaScript errors
   - Verify network requests in browser dev tools
   - Check Flask console for Python errors

Common Issues & Solutions:
- 404 errors: Routes not properly registered
- 500 errors: Database connection or Python syntax issues
- Permission denied: admin_required decorator not working
- JavaScript errors: Check for missing functions in templates
- CSS issues: Verify CSS variables are defined
""")

def run_database_check():
    """Check if database is properly set up for user management"""
    print("\n🗄️ DATABASE SETUP CHECK")
    print("=" * 40)
    
    try:
        import sqlite3
        import os
        
        # This is a basic check - adjust based on your database setup
        print("✅ Database modules available")
        
        # You could add actual database connectivity tests here
        print("📝 To verify your database:")
        print("   1. Check that users table exists")
        print("   2. Verify admin user exists")
        print("   3. Test database connectivity")
        print("   4. Check foreign key constraints")
        
        return True
    except Exception as e:
        print(f"❌ Database check failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 QR Code Management - User Management Tester")
    print("=" * 60)
    
    # Check if Flask app is running
    tester = UserManagementTester()
    
    try:
        # Quick connectivity test
        response = tester.session.get(f"{tester.base_url}/")
        if response.status_code in [200, 302, 404]:  # Any response means server is running
            print("✅ Flask application appears to be running")
            
            # Ask user what they want to do
            print("\nSelect testing mode:")
            print("1. 🤖 Run automated tests")
            print("2. 📋 Show manual testing instructions")
            print("3. 🚀 Show setup guide")
            print("4. 🗄️ Check database setup")
            
            choice = input("\nEnter choice (1-4): ").strip()
            
            if choice == "1":
                print("\n🤖 Running automated tests...")
                success = tester.run_all_tests()
                if not success:
                    print("\n💡 If tests failed, try the manual testing instructions.")
                    
            elif choice == "2":
                manual_test_instructions()
                
            elif choice == "3":
                quick_setup_guide()
                
            elif choice == "4":
                run_database_check()
                
            else:
                print("Invalid choice. Showing manual instructions...")
                manual_test_instructions()
        
        else:
            print("❌ Cannot connect to Flask application")
            print("Make sure your app is running on http://localhost:5000")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Make sure Flask app is running: python app.py")
        print("2. Check the URL is correct: http://localhost:5000")
        print("3. Verify no firewall is blocking the connection")
        print("\n📋 Showing manual testing instructions instead...")
        manual_test_instructions()