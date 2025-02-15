from flask import Flask,render_template,request,flash,redirect,url_for,jsonify,session
import pymysql
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)
def get_connection():
    return pymysql.connect(host='localhost',
                           user='root',
                           password='yadu2002',
                           database='e_learning',
                           port=3306
    )
con = get_connection()
cursor = con.cursor()

# email configuration
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USER = "your_email@gmail.com"
EMAIL_PASS = "your_email_password"  # Use an App Password if using Gmail

reset_tokens = {}


# for upload_folder initialization
app.config['UPLOAD_FOLDER'] = 'uploads'
allowed_extensions = {'pdf','doc','docx','txt'}


# login & signup & forgot password
@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    print(f"Received login request - Username: {username}, Password: {password}")
    if not username or not password:
        return jsonify({"success": False, "message": "Please enter username and password!"})
    
    cursor.execute('SELECT id, username, password, role FROM users WHERE username=%s', (username,))
    data = cursor.fetchone()

    print(f"Database query result: {data}")

    if data:
        user_id, db_username, db_password, role = data

        if check_password_hash(db_password, password):
            session['user_id'] = user_id
            session['username'] = db_username
            session['role'] = role
            return jsonify({"success": True, "role": role, "redirect": url_for(f'{role}', user_id=user_id)})
        else:
            return jsonify({"success": False, "message": "Invalid password!"})
            
    return jsonify({"success": False, "message": "User not found!"})

    
@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/sign_up',methods=['post'])
def sign_up():
    name = request.form['username']
    email = request.form['email']
    password = request.form['password']

    hashedPassword = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    try:
        cursor.execute(
            "INSERT INTO users (username, email, role, password) VALUES (%s, %s, %s, %s)",
            (name, email, 'student', hashedPassword)
        )
        con.commit()
        return jsonify({"success": True, "message": "Account created successfully! Please log in."})  
    except pymysql.MySQLError as e:
        con.rollback()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})


@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    email = request.form.get('email')

    if not email:
        flash("Please enter your email!", "danger")
        return redirect(url_for('forgot_password_page'))

    # 🔹 Check if email exists
    cursor.execute("SELECT id FROM users WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        flash("Email not found!", "danger")
        return redirect(url_for('forgot_password_page'))

    user_id = user[0]

    # 🔹 Generate Secure Token
    token = secrets.token_urlsafe(32)
    reset_tokens[token] = user_id  # Temporarily store token (use DB in production)

    # 🔹 Send Reset Link via Email
    reset_link = f"http://127.0.0.1:5000/reset_password/{token}"
    email_body = f"Click the link below to reset your password:\n\n{reset_link}"

    msg = MIMEText(email_body)
    msg["Subject"] = "Password Reset Request"
    msg["From"] = EMAIL_USER
    msg["To"] = email

    try:
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, email, msg.as_string())
        server.quit()
        flash("Password reset link sent! Check your email.", "success")
    except Exception as e:
        flash(f"Error sending email: {e}", "danger")

    return redirect(url_for('forgot_password_page'))

# 🔹 Render Forgot Password Page
@app.route('/forgot_password')
def forgot_password_page():
    return render_template('forgot.html')

# 🔹 Reset Password Form (Step 2)
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if token not in reset_tokens:
        flash("Invalid or expired token!", "danger")
        return redirect(url_for('forgot_password_page'))

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Passwords do not match!", "danger")
            return render_template('reset_password.html', token=token)

        user_id = reset_tokens[token]  # Get user_id from stored token

        # 🔹 Update Password in Database
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256', salt_length=16)
        cursor.execute("UPDATE users SET password=%s WHERE id=%s", (hashed_password, user_id))
        con.commit()

        del reset_tokens[token]  # Remove token after use

        flash("Password reset successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)


# adim and its functionalities
@app.route('/admin_page/<int:user_id>')
def admin(user_id):
    return render_template('admin.html')

@app.route('/admin_page/adduser')
def adduser():
    return render_template('adduser.html')

@app.route('/add_user',methods=['post'])
def add_user():
    email = request.form['email']
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    cursor.execute('insert into users(username,email,role,password) values(%s,%s,%s,%s)',(username,email,role,hashed_password))
    con.commit()
    return jsonify({"success":True, "message":"user added successfully!"} )

@app.route('/admin_page/edituser')
def edituser():
    return render_template('edituser.html')

@app.route('/edit_user',methods=['post'])
def edit_user():
    print(request.form)
    name = request.form['username']
    cursor.execute('select id, username,email,role from users where username=%s',(name,))
    data = cursor.fetchone()
    if data:
        return jsonify({"success":True, "id":data[0], "username":data[1],"email":data[2], "role":data[3] }),200
@app.route('/update_user',methods=['post'])
def update_user():
    try:
        id = request.form.get('user_id')

        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role')

        if not email or not username or not password or not role:
            return jsonify({"success": False, "error": "All fields are required!"}), 400

        # Hash the password
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
        print("Hashed Password:", hashed_password)  # Debugging

        # Check if the user exists
        cursor.execute("SELECT * FROM users WHERE id = %s", (id,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "error": "User not found!"}), 404

        print("Received role:", role)  # Debugging

        # Update user
        cursor.execute("UPDATE users SET username=%s,email=%s, role=%s, password=%s WHERE id=%s",
                       (username, email, role, hashed_password, id))
        con.commit()  # Ensure the update is saved

        return jsonify({"success": True, "message": "User updated successfully!"}), 200

    except Exception as e:
        print("Error:", str(e))  # Debugging
        return jsonify({"success": False, "error": str(e)}), 500
    
@app.route('/deleteuser')    
def deleteuser():
    return render_template('deleteuser.html')

@app.route('/delete_user', methods=['POST'])
def delete_user():
    username = request.form.get('username')  # Use .get() for safety
    print(f"Searching for username: {username}")  # Debugging log
    
    cursor.execute('SELECT id FROM users WHERE username=%s', (username,))
    data = cursor.fetchone()
    
    if data:
        print(f"User found! ID: {data[0]}")  # Debugging log
        return jsonify({"success": True, "user_id": data[0]}), 200
    else:
        print("User not found!")  # Debugging log
        return jsonify({"success": False, "message": "User not found!"}), 200  # Explicit status

@app.route('/remove_user',methods=['post'])
def remove_user():
    id = request.form.get('user_id')
    cursor.execute('delete from users where id=%s',(id,))
    con.commit()
    return jsonify({"success":True, "message":"user removed successfully!"}),200

@app.route('/admin_page/viewuser')
def viewuser():
    cursor.execute('select * from users')
    data = cursor.fetchall()

    users_data = [{"id": user[0], "name": user[1], "email": user[2], "role": user[3]} for user in data]

    return render_template('viewuser.html', users=users_data)
@app.route('/admin_page/viewcourse')
def viewcourse():
    cursor.execute('select * from courses')
    data = cursor.fetchall()
    courseList = [{"id": course[0], "name": course[1], "description": course[2]} for course in data]
    return render_template('viewcourse.html', courses=courseList)

@app.route('/admin_page/viewresource')
def viewresource():
    cursor.execute('select * from resources')
    data = cursor.fetchall()
    resourceList = [{"id": resource[0], "course": resource[1], "name": resource[2], "path": resource[3], "type": resource[4]}for resource in data]
    return render_template('viewresource.html', resources=resourceList)

# tutor and its functionalities
@app.route('/tutor/<int:user_id>')
def tutor(user_id):
    cursor.execute("SELECT id, name FROM courses WHERE tutor_id=%s", (user_id,))
    courses = cursor.fetchall()

    courses_data = []
    for course in courses:
        course_id, course_name = course
        cursor.execute("SELECT id, name, file_url FROM resources WHERE course_id=%s", (course_id,))
        resources = cursor.fetchall()

        courses_data.append({
            "id": course_id,
            "name": course_name,
            "resources": [{"id": r[0], "name": r[1], "path": r[2]} for r in resources]
        })

    return render_template('tutor.html', courses=courses_data, user_id=user_id)

@app.route('/tutor/add_course')
def add_course_form():
    cursor.execute("select r.id, c.name, r.name from resources r join courses c on r.course_id = c.id where c.tutor_id = %s", (session['user_id'],))
    resources = cursor.fetchall()
    return render_template('add_course.html', resources=resources)
    
@app.route('/add_course', methods=['post'])
def add_course():
    try:
        course_name = request.form['courseName']
        tutor_name = request.form['tutorName']
        course_description = request.form['courseDescription']
        resource_type = request.form['resourceType']
        resource_name = request.form.get('resourceName', '')  # Optional field
        resource_file = request.files.get('resourceFile')  # File input
        resource_link = request.form.get('resourceLink', '')  # URL input

        # 🔹 Get tutor_id
        cursor.execute("SELECT id FROM users WHERE username=%s AND role=%s", (tutor_name, 'tutor'))
        tutor = cursor.fetchone()

        if not tutor:
            flash("Tutor not found!", "danger")
            return redirect(url_for("admin_page"))

        tutor_id = tutor['id']

        # 🔹 Check if course already exists
        cursor.execute("SELECT id FROM courses WHERE name=%s", (course_name,))
        existing_course = cursor.fetchone()

        if existing_course:
            flash("Course already exists!", "warning")
            return redirect(url_for("admin_page"))

        # 🔹 Insert course
        cursor.execute("INSERT INTO courses (name, tutor_id, description) VALUES (%s, %s, %s)", 
                       (course_name, tutor_id, course_description))
        con.commit()

        # 🔹 Get the new course_id
        cursor.execute("SELECT id FROM courses WHERE name=%s", (course_name,))
        course = cursor.fetchone()

        if not course:
            flash("Failed to retrieve course ID!", "danger")
            return redirect(url_for("admin_page"))

        course_id = course['id']

        # 🔹 Handle Resource Based on Type
        file_path = None

        file_extension = resource_file.filename.rsplit('.', 1)[-1].lower()
        if resource_type == "pdf" and resource_file and file_extension in allowed_extensions:

            filename = secure_filename(resource_file.filename)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            resource_file.save(file_path)
            file_path = file_path.replace("\\", "/")  # Normalize path

        elif resource_type == "link":
            file_path = resource_link

        elif resource_type == "book":
            file_path = None  # Handle book storage separately if needed

        # 🔹 Insert into resources table
        if resource_name and file_path:
            cursor.execute("INSERT INTO resources (course_id, name, file_url) VALUES (%s, %s, %s)", 
                           (course_id, resource_name, file_path))
            con.commit()

        flash("Course and resource added successfully!", "success")

    except Exception as e:
        con.rollback()
        flash(f"Error: {e}", "danger")
        print(f"Error: {e}")

    return redirect(url_for("admin_page"))


#delete course using button
@app.route('/delete-resource', methods=['POST'])
def delete_resource():
    data = request.get_json()
    resource_id = data.get('resource_id')

    if not resource_id:
        return jsonify({'error': 'Resource ID is required'}), 400

    try:
        with con.cursor() as cursor:
            sql = "DELETE FROM resources WHERE id = %s"
            cursor.execute(sql, (resource_id,))
    finally:
        con.close()

    return jsonify({'success': True, 'message': 'Resource deleted successfully'})



# student and its functionalities
@app.route('/student/<int:user_id>')
def student(user_id):
    cursor.execute('select c.name, c.description from courses c join enrollments e on c.id = e.course_id where e.user_id = %s', (user_id,))
    data = cursor.fetchall()

    cursor.execute('SELECT c.id, c.course_name FROM enrollments e JOIN courses c ON e.course_id = c.id  WHERE e.student_id = %s', (user_id,))
    data1 = cursor.fetchall()

    return render_template('student.html', available_courses=data, enrolled_courses=data1, user_id=user_id)

@app.route('/enroll', methods=['POST'])
def enroll():
    student_id = request.json.get('student_id')  # Get student ID from frontend
    course_id = request.json.get('course_id')  # Get course ID from frontend

    if not student_id or not course_id:
        return jsonify({"error": "Missing student_id or course_id"}), 400

    # Check if the student is already enrolled
    cursor.execute("SELECT * FROM enrollments WHERE student_id = %s AND course_id = %s", (student_id, course_id))
    existing = cursor.fetchone()

    if existing:
        return jsonify({"message": "Already enrolled"}), 409  # Conflict response

    # Insert into enrollments table
    cursor.execute("INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s)", (student_id, course_id))
    con.commit()
    
    return jsonify({"message": "Enrolled successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)