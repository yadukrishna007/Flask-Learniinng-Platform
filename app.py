from flask import Flask,render_template,request,flash,redirect,url_for
import pymysql
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash,generate_password_hash

app = Flask(__name__)
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

@app.route('/login',methods=['post'])
def login():
    username = request.form['username']
    password = request.form['password']

    cursor.execute('select id,username,password,role from users where username=%s',(username,))
    data = cursor.fetchone()


    if data:
        user_id, db_username, db_password, role = data

        if check_password_hash(db_password,password):
            if role == 'admin':
                return render_template('admin.html')
            elif role == 'tutor':
                return render_template('tutor.html')
            else:
                return render_template('student.html')
        else:
            return "password doesnt match!!!"
            
            
    else:
        return 'login failed'
    
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
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    except pymysql.MySQLError as e:
        con.rollback()
        flash(f"Error: {e}", "danger")
        return render_template('login.html')


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
@app.route('/admin_page')
def admin():
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
    cursor.execute('insert into users(username,email,role,password) values(%s,%s,%s,%s)',(username,email,role,password))
    con.commit()
    return 'user added'

@app.route('/admin_page/edituser')
def edituser():
    return render_template('edituser.html')

@app.route('/get_user',methods=['post'])
def edit_user():
    name = request.form['username']
    cursor.execute('select * from users where username=%s',(name,))
    data = cursor.fetchone()
    return render_template('edituser.html',data=data)

@app.route('/update_user',methods=['post'])
def update_user():
    email = request.form['email']
    name = request.form['username']
    password = request.form['password']
    role = request.form['role']
    hashed_password = generate_password_hash(password,method='pbkdf2:sha256', salt_length=16)
    cursor.execute('INSERT INTO users (username, email, role, password) VALUES (%s, %s, %s, %s)', (name, email, role, hashed_password))
    con.commit()
    return 'user updated'

@app.route('/admin_page/deleteuser')
def deleteuser():
    return render_template('deleteuser.html')

@app.route('/delete_user',methods=['post'])
def delete_user():
    name = request.form['username']
    cursor.execute('select * from users where username=%s',(name,))   
    data = cursor.fetchone()
    if data:
        return render_template('edituser.html',data=data)
    else:
        flash("User not found","danger")
        return redirect(url_for('deleteuser'))

@app.route('/remove_user',methods=['post'])
def remove_user():
    id = request.form['user_id']
    cursor.execute('delete from users where id=%s',(id,))
    con.commit()
    return 'user deleted'

@app.route('/admin_page/viewuser')
def viewuser():
    cursor.execute('select * from users')
    data = cursor.fetchall()
    return render_template('viewuser.html',data=data)

@app.route('/admin_page/viewcourse')
def viewcourse():
    cursor.execute('select * from courses')
    data = cursor.fetchall()
    return render_template('viewcourse.html',data=data)

@app.route('/admin_page/viewresource')
def viewresource():
    cursor.execute('select * from resources')
    data = cursor.fetchall()
    return render_template('viewresource.html',data=data)

# tutor and its functionalities
@app.route('/tutor')
def tutor():
    return render_template('tutor.html')

@app.route('/tutor/add_course')
def add_course_form():
    return render_template('add_course.html')

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


# student and its functionalities
@app.route('/student')
def student():
    return render_template('student.html')


if __name__ == '__main__':
    app.run(debug=True)