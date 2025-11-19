📘 EduPro – Learning Management System (LMS)

EduPro is a modern, full-featured Learning Management System (LMS) built using Django.
It supports role-based login, video learning, trainer–student interaction, payments, ratings, and feedback — designed for training institutes, academies, and online education platforms.

🚀 Features:

👨‍🎓 Student Features:
-> View assigned courses, modules, and video lessons
-> Submit video feedback
-> Rate trainers (1–5 stars)
-> Track all payments inside the Student Dashboard
-> Update personal profile
-> Dependent dropdown for Country → State → District
-> View certificates or course completion status (if enabled)

👨‍🏫 Trainer Features
-> Trainer dashboard with assigned students
-> Upload videos, materials, tasks
-> View student ratings & feedback
-> Manage course content

🛠️ Admin Features
-> Add/edit courses & modules
-> Manage trainers & students
-> Approve payments
-> View all feedback & ratings
-> Dashboard analytics

🧩 Tech Stack:
-> Backend:Django 5+
-> Database:SQLite / PostgreSQL / MySQL
-> Frontend:HTML, CSS, Bootstrap
-> Authentication:Django AllAuth
-> Media Storage:Local 

📂 Project Structure
EduPro/
│── core/              → Main Django app  
│── students/          → Student module  
│── trainers/          → Trainer module  
│── courses/           → Courses & videos  
│── payments/          → Payment tracking  
│── templates/         → HTML templates  
│── static/            → CSS, JS, images  
│── manage.py

⚙️ Installation
1️⃣ Clone the repository
git clone https://github.com/harinimurugadoss/edupro.git
cd edupro

2️⃣ Create virtual environment
python -m venv venv
venv\Scripts\activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Run migrations
python manage.py migrate

5️⃣ Start development server
python manage.py runserver
