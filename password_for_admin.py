from werkzeug.security import generate_password_hash

# Admin password
admin_password = "admin123"

# Generate hashed password
hashed_password = generate_password_hash(admin_password)

# Print the hashed password (Copy this for your SQL insert)
print("Hashed Password:", hashed_password)
