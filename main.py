import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort,send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import aliased
from sqlalchemy import func
from sqlalchemy.orm import joinedload

curr_dir = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///serviceapp.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "letsencrypt"
app.config['PASSWORD_HASH'] = 'sha512'

app.config['UPLOAD_EXTENSIONS'] = ['.pdf']
app.config['UPLOAD_PATH'] = os.path.join(curr_dir, 'static', "pdfs")

db = SQLAlchemy()

db.init_app(app)
app.app_context().push()


class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    pincode = db.Column(db.Integer)
    is_admin = db.Column(db.Boolean, default=False)
    is_professional = db.Column(db.Boolean, default=False)
    is_homeowner = db.Column(db.Boolean, default=False)
    

class Homeowner(db.Model):
    __tablename__ = 'homeowners'
    
    homeowner_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)  
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=True)
    service_request = db.Column(db.Text)
    rating = db.Column(db.Float)
    review = db.Column(db.Text)

    user = db.relationship('User', backref=db.backref('homeowner', uselist=False))

class Professional(db.Model):
    __tablename__ = 'professionals'
    
    professional_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), primary_key=True)  
    service_name = db.Column(db.String(100))
    experience = db.Column(db.Integer)
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    description_file = db.Column(db.Text)
    avg_rating = db.Column(db.Float)
    user = db.relationship('User', backref=db.backref('professional', uselist=False))

class Service(db.Model):
    __tablename__ = 'services'
    
    service_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_name = db.Column(db.String(100), nullable=False)
    service_description = db.Column(db.Text)
    base_price = db.Column(db.Float)
    time_required = db.Column(db.Integer)
    rating_count = db.Column(db.Integer)

class ServiceRequest(db.Model):
    __tablename__ = 'service_requests'
    
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.Integer, db.ForeignKey('services.service_id'), nullable=False)
    homeowner_id = db.Column(db.Integer, db.ForeignKey('homeowners.homeowner_id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('professionals.professional_id'), nullable=False)
    service_name = db.Column(db.String(100))
    service_status = db.Column(db.String(50), default="None")
    rating_by_owner = db.Column(db.Float)
    review_by_owner = db.Column(db.Text)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    date_closed = db.Column(db.DateTime)



def setup():
    db.create_all()
    admin_user = User.query.filter_by(username='admin').first()
    if not admin_user:
        admin = User(
            username='admin',
            email='admin@localhost',
            address='Admin Address',
            pincode=123456,
            password=generate_password_hash('1234', method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created!")


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        print(f"Attempting login with username: {username}")
        user = User.query.filter_by(username=username).first()
        print(f"User found: {user}")
        if user:
            print(f"Stored password hash: {user.password}")
            if check_password_hash(user.password, password):
                session['user_id'] = user.user_id
                session['username'] = user.username
                session['is_homeowner'] = user.is_homeowner
                session['is_professional'] = user.is_professional
                if user.is_homeowner:
                    return redirect(url_for('homeowner_dashboard'))
                elif user.is_professional:
                    return redirect(url_for('professional_dashboard'))
                else:
                    flash('Invalid user role.', 'danger')
                    return redirect(url_for('login'))
            else:
                flash('Invalid username or password. Please try again.', 'danger')
                return redirect(url_for('login'))
        else:
            flash('User not found. Please check your credentials and try again.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            if user.is_admin: 
                session['user_id'] = user.user_id 
                return redirect(url_for('admin_dashboard'))
            else:
                flash('You are not an admin.', 'danger') 
        else:
            flash('Invalid username or password.', 'danger') 

    return render_template('admin_login.html')

@app.route('/register_homeowner', methods=['GET', 'POST'])
def register_homeowner():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        email = request.form['email']
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('User already has an account! Please log in.', 'danger')
            return redirect(url_for('login'))
        address = request.form['address']
        pincode = request.form['pincode']
        new_user = User(username=username, password=password, email=email, address=address, pincode=pincode, is_homeowner=True)
        db.session.add(new_user)
        db.session.commit()
        new_homeowner = Homeowner(homeowner_id=new_user.user_id)
        db.session.add(new_homeowner)
        db.session.commit()
        flash('Homeowner registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register_homeowner.html')

@app.route('/register_professional', methods=['GET', 'POST'])
def register_professional():
    description_folder = os.path.join(app.root_path, 'static', 'description_files')
    os.makedirs(description_folder, exist_ok=True)
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
            email = request.form['email']
            service_id = request.form['service_name']
            experience = request.form['experience']
            pincode = request.form['pincode']
            address = request.form['address']
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash('User already has an account! Please log in.', 'danger')
                return redirect(url_for('login'))
            file = request.files['description_file']
            if not file or not file.filename.endswith('.pdf'):
                flash('Invalid file format. Only PDF files are allowed.', 'danger')
                return redirect(url_for('register_professional'))
            filename = secure_filename(f"{username}.pdf")
            file_path = os.path.join(description_folder, filename)
            file.save(file_path)
            service = Service.query.get(service_id)
            if not service:
                flash('Selected service is not available. Please choose a valid service.', 'danger')
                return redirect(url_for('register_professional'))
            new_user = User(
                username=username,
                password=password,
                email=email,
                address=address,
                pincode=pincode,
                is_professional=True,
                is_homeowner=False
            )
            db.session.add(new_user)
            db.session.commit()
            professional = Professional(
                professional_id=new_user.user_id,
                service_name=service.service_name,
                experience=experience,
                service_id=service.service_id,
                description_file=file_path,
                is_approved=False
            )
            db.session.add(professional)
            db.session.commit()
            flash('Professional registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            print(f"Error during registration: {e}")
            flash('An error occurred during registration. Please try again.', 'danger')
            return redirect(url_for('register_professional'))
    services = Service.query.all()
    return render_template('register_professional.html', services=services)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    services = Service.query.all()
    unapproved_professionals = Professional.query.filter_by(is_approved=False).all()
    service_requests = ServiceRequest.query \
        .join(Service, ServiceRequest.service_id == Service.service_id) \
        .join(Homeowner, ServiceRequest.homeowner_id == Homeowner.homeowner_id) \
        .join(Professional, ServiceRequest.professional_id == Professional.professional_id) \
        .add_columns(
            ServiceRequest.request_id,
            Service.service_name,
            Homeowner.homeowner_id,
            Professional.professional_id,
            ServiceRequest.service_status,
            ServiceRequest.rating_by_owner,
            ServiceRequest.review_by_owner,
            ServiceRequest.date_created,
            ServiceRequest.date_closed
        ).all()

    if request.method == 'POST':
        if 'create_service' in request.form:
            service_name = request.form['service_name']
            base_price = float(request.form['base_price'])
            description = request.form['description']
            time_required = int(request.form['time_required'])
            new_service = Service(
                service_name=service_name.capitalize(),
                base_price=base_price,
                service_description=description,
                rating_count=0,
                time_required=time_required
            )
            db.session.add(new_service)
            db.session.commit()
            flash("Service created successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        elif 'edit_service' in request.form:
            service_id = request.form['service_id']
            service = Service.query.get_or_404(service_id)
            service.service_name = request.form['service_name']
            service.base_price = float(request.form['base_price'])
            service.service_description = request.form['description']
            service.time_required = int(request.form['time_required'])
            db.session.commit()
            flash("Service updated successfully!", "success")
            return redirect(url_for('admin_dashboard'))
        elif 'delete_service' in request.form:
            service_id = request.form['service_id']
            service = Service.query.get_or_404(service_id)
            db.session.delete(service)
            db.session.commit()
            flash(f"Service '{service.service_name}' deleted successfully!", "danger")
            return redirect(url_for('admin_dashboard'))
        elif 'approve_professional' in request.form:
            professional_id = request.form['professional_id']
            professional = Professional.query.get_or_404(professional_id)
            professional.is_approved = True
            db.session.commit()
            flash(f"Professional {professional.user.username} approved!", "success")

        elif 'reject_professional' in request.form:
            professional_id = request.form['professional_id']
            professional = Professional.query.get_or_404(professional_id)
            professional.is_approved = False
            db.session.commit()
            flash(f"Professional {professional.user.username} rejected.", "danger")

        unapproved_professionals = Professional.query.filter_by(is_approved=False).all()
        return redirect(url_for('admin_dashboard'))

    if request.args.get('view_pdf'):
        professional_id = int(request.args.get('view_pdf'))
        professional = Professional.query.get_or_404(professional_id)
        file_path = os.path.join(app.root_path, 'static', professional.description_file)

        if not os.path.exists(file_path):
            flash("File not found!", "danger")
            return redirect(url_for('admin_dashboard'))

        return send_file(file_path, as_attachment=False)

    return render_template(
        'admin_dashboard.html',is_admin=True,
        services=services,
        unapproved_professionals=unapproved_professionals,
        service_requests=service_requests,
    )

@app.route('/homeowner_dashboard', methods=['GET', 'POST'])
def homeowner_dashboard():
    user_id = session.get('user_id') 
    user = User.query.get(user_id)
    homeowner = Homeowner.query.filter_by(homeowner_id=user_id).first()

    if not homeowner:
        flash("Homeowner not found", "danger")
        return redirect(url_for('login'))

    def fetch_service_history():
        return (
            db.session.query(
                ServiceRequest.request_id,
                User.username.label("professional_name"),
                ServiceRequest.service_status,
                ServiceRequest.rating_by_owner,
                ServiceRequest.review_by_owner,
                ServiceRequest.date_created,
                ServiceRequest.date_closed,
            )
            .join(Professional, ServiceRequest.professional_id == Professional.professional_id)
            .join(User, Professional.professional_id == User.user_id)
            .filter(ServiceRequest.homeowner_id == homeowner.homeowner_id)
            .order_by(ServiceRequest.date_created.desc())
            .all()
        )

    service_history = fetch_service_history()

    available_services = Service.query.all()

    if request.method == 'POST':

        if 'close_service' in request.form:
            request_id = request.form.get('request_id')
            rating = request.form.get('rating')
            review = request.form.get('review')

            service_request = ServiceRequest.query.get(request_id)

            if service_request and service_request.service_status == 'Accepted':
                try:
                    service_request.service_status = 'Completed'
                    service_request.rating_by_owner = float(rating)
                    service_request.review_by_owner = review
                    service_request.date_closed = datetime.utcnow()

                    professional = Professional.query.get(service_request.professional_id)
                    if professional:
                        all_ratings = (
                            db.session.query(ServiceRequest.rating_by_owner)
                            .filter(
                                ServiceRequest.professional_id == professional.professional_id,
                                ServiceRequest.rating_by_owner.isnot(None)
                            )
                            .all()
                        )
                        all_ratings_values = [r[0] for r in all_ratings]
                        professional.avg_rating = sum(all_ratings_values) / len(all_ratings_values)

                    service = Service.query.get(service_request.service_id)
                    if service:
                        service.rating_count = service.rating_count + 1 if service.rating_count else 1

                    db.session.commit()
                    flash("Service marked as completed and feedback recorded successfully!", "success")

                    service_history = fetch_service_history()
                except Exception as e:
                    db.session.rollback()
                    flash(f"An error occurred: {e}", "danger")

    return render_template(
        'homeowner_dashboard.html',
        is_homeowner=True,
        homeowner=homeowner,
        service_history=service_history,
        services=available_services
    )

@app.route('/service_details/<string:service_name>', methods=['GET', 'POST'])
def service_details(service_name):
    service = Service.query.filter_by(service_name=service_name).first()
    if not service:
        flash(f"Service '{service_name}' not found.", "danger")
        return redirect(url_for('homeowner_dashboard'))

    time_required = service.time_required
    homeowner_id = session.get('user_id')

    if not homeowner_id:
        flash("You must be logged in to access this page.", "warning")
        return redirect(url_for('login'))

    approved_professionals = Professional.query.filter_by(
        service_id=service.service_id, is_approved=True
    ).all()


    ProfessionalUser = aliased(User)
    service_history = (
        db.session.query(
            ServiceRequest.request_id,
            ServiceRequest.service_status,
            ServiceRequest.rating_by_owner,
            ServiceRequest.review_by_owner,
            ServiceRequest.date_created,
            ServiceRequest.date_closed,
            User.username.label('homeowner_name'),
            ProfessionalUser.username.label('professional_name'),
        )
        .join(Homeowner, ServiceRequest.homeowner_id == Homeowner.homeowner_id)
        .join(User, Homeowner.homeowner_id == User.user_id)
        .join(Professional, ServiceRequest.professional_id == Professional.professional_id)
        .join(ProfessionalUser, Professional.professional_id == ProfessionalUser.user_id)
        .filter(ServiceRequest.homeowner_id == homeowner_id)
        .order_by(ServiceRequest.date_created.desc())
        .all()
    )

    if request.method == 'POST':
        if 'professional_id' in request.form:
            professional_id = request.form.get('professional_id')

            try:

                new_request = ServiceRequest(
                    service_id=service.service_id,
                    homeowner_id=homeowner_id,
                    professional_id=professional_id,
                    service_status="Pending",
                    date_created=db.func.now(),
                )
                db.session.add(new_request)
                db.session.commit()
                flash("Service rebooked successfully! Awaiting professional confirmation.", "success")
                return redirect(url_for('service_details', service_name=service_name))
            except Exception as e:
                db.session.rollback()
                flash(f"An error occurred while rebooking: {e}", "danger")

        elif 'close_service' in request.form:
            request_id = request.form.get('request_id')
            rating = request.form.get('rating', type=float)
            review = request.form.get('review')

            service_request = ServiceRequest.query.get(request_id)

            if service_request and service_request.homeowner_id == homeowner_id:
                try:
                    service_request.service_status = "Completed"
                    service_request.rating_by_owner = rating
                    service_request.review_by_owner = review

                    professional = Professional.query.get(service_request.professional_id)
                    if professional:
                        avg_rating = (
                            db.session.query(db.func.avg(ServiceRequest.rating_by_owner))
                            .filter(ServiceRequest.professional_id == professional.professional_id)
                            .scalar()
                        )
                        professional.avg_rating = avg_rating or 0

                    db.session.commit()
                    flash("Service marked as completed. Thank you for your feedback!", "success")
                except Exception as e:
                    db.session.rollback()
                    flash(f"Error updating service: {e}", "danger")
            else:
                flash("Invalid service request.", "danger")
            return redirect(url_for('service_details', service_name=service_name))

    avg_rating = (
        db.session.query(db.func.avg(ServiceRequest.rating_by_owner))
        .filter(ServiceRequest.service_id == service.service_id)
        .scalar()
    )
    avg_rating = float(avg_rating) if avg_rating else 0.0

    for professional in approved_professionals:
        professional.avg_rating = (
            db.session.query(db.func.avg(ServiceRequest.rating_by_owner))
            .filter(ServiceRequest.professional_id == professional.professional_id)
            .scalar() or 0
        )
        professional.avg_rating = round(professional.avg_rating, 2)
        professional.time_required = time_required

    return render_template(
        'service_details.html',
        is_homeowner=True,
        service=service,
        avg_rating=avg_rating,
        approved_professionals=approved_professionals,
        service_history=service_history,
        time_required=time_required,
    )

@app.route('/professional_dashboard', methods=['GET', 'POST'])
def professional_dashboard():
    user_id = session.get('user_id') 
    user = User.query.get(user_id)
    professional = Professional.query.filter_by(professional_id=user_id).first()

    if not professional:
        flash("Professional not found", "danger")
        return redirect(url_for('login'))

    if not professional.is_approved: 
        return render_template('professional_dashboard.html', professional=professional, service_requests=[], closed_services=[], ongoing_services=[])

    service_requests = (
        db.session.query(
            ServiceRequest.request_id,
            Homeowner.homeowner_id,
            User.username.label("homeowner_name"),
            User.email.label("homeowner_email"),
            User.pincode.label("homeowner_pincode"),
            ServiceRequest.service_status,
            ServiceRequest.date_created
        )
        .join(Homeowner, ServiceRequest.homeowner_id == Homeowner.homeowner_id)
        .join(User, Homeowner.homeowner_id == User.user_id)
        .filter(ServiceRequest.professional_id == professional.professional_id)
        .filter(ServiceRequest.service_status.in_(["Pending", "Accepted"])) 
        .order_by(ServiceRequest.date_created.desc())
        .all()
    )


    ongoing_services = (
        db.session.query(
            ServiceRequest.request_id,
            Homeowner.homeowner_id,
            User.username.label("homeowner_name"),
            User.email.label("homeowner_email"),
            User.pincode.label("homeowner_pincode"),
            ServiceRequest.service_status,
            ServiceRequest.date_created
        )
        .join(Homeowner, ServiceRequest.homeowner_id == Homeowner.homeowner_id)
        .join(User, Homeowner.homeowner_id == User.user_id)
        .filter(ServiceRequest.professional_id == professional.professional_id)
        .filter(ServiceRequest.service_status == "Accepted")
        .order_by(ServiceRequest.date_created.desc())
        .all()
    )


    closed_services = (
        db.session.query(
            Homeowner.homeowner_id,
            User.username.label("homeowner_name"),
            ServiceRequest.rating_by_owner,
            ServiceRequest.review_by_owner,
            ServiceRequest.date_created,
            ServiceRequest.date_closed
        )
        .join(Homeowner, ServiceRequest.homeowner_id == Homeowner.homeowner_id)
        .join(User, Homeowner.homeowner_id == User.user_id)
        .filter(ServiceRequest.professional_id == professional.professional_id)
        .filter(ServiceRequest.service_status == "Completed")
        .order_by(ServiceRequest.date_closed.desc())
        .all()
    )

    if request.method == 'POST':

        if 'update_profile' in request.form:
            user.username = request.form['username']
            user.email = request.form['email']
            user.address = request.form['address']
            user.pincode = request.form['pincode']
            db.session.commit()
            flash("Profile updated successfully!", "success")
            return redirect(url_for('professional_dashboard'))

        elif 'service_action' in request.form:
            service_request_id = request.form['service_request_id']
            action = request.form['action']
            service_request = ServiceRequest.query.get(service_request_id)

            if service_request:
                if action == "accept":
                    service_request.service_status = "Accepted"
                elif action == "reject":
                    service_request.service_status = "Rejected"
                db.session.commit()
                flash(f"Service request has been {action}ed.", "success")
                return redirect(url_for('professional_dashboard'))

    return render_template(
        'professional_dashboard.html',is_professional=True,
        professional=professional,
        service_requests=service_requests,
        ongoing_services=ongoing_services,
        closed_services=closed_services
    )





@app.route('/homeowner_search', methods=['GET', 'POST'])
def homeowner_search():
    services = db.session.query(
        Service.service_id,
        Service.service_name,
        Professional.professional_id,
        User.username.label('professional_name'),
        User.address,
        User.pincode,
        Professional.avg_rating
    ).join(Professional, Service.service_id == Professional.service_id)\
     .join(User, Professional.professional_id == User.user_id).all()

    homeowner_id = session.get('user_id')
    service_requests = ServiceRequest.query.filter_by(homeowner_id=homeowner_id).all()

    service_status_map = {req.service_id: req.service_status for req in service_requests}

    search_type = request.form.get('search_type', 'professional_id')
    search_query = request.form.get('search_query')

    search_options = {
        "professional_id": sorted(set([str(service.professional_id) for service in services])),
        "professional_name": sorted(set([service.professional_name for service in services])),
        "service_id": sorted(set([str(service.service_id) for service in services])),
        "service_name": sorted(set([service.service_name for service in services])),
        "rating": [
            ">4.5",
            "4.5<rating<=4.0",
            "4.0<rating<=3.5",
            "3.5<rating<=3.0",
            "3.0<rating<=2.5",
            "2.5<rating<=2.0",
            "2.0<rating<=1.5",
            "1.5<rating<=1.0"
        ],
        "address": sorted(set([service.address for service in services if service.address])),
        "pincode": sorted(set([service.pincode for service in services if service.pincode])),
    }

    filtered_services = services
    if search_query:
        if search_type == 'professional_id':
            filtered_services = [s for s in services if str(s.professional_id) == search_query]
        elif search_type == 'professional_name':
            filtered_services = [s for s in services if s.professional_name == search_query]
        elif search_type == 'service_id':
            filtered_services = [s for s in services if str(s.service_id) == search_query]
        elif search_type == 'service_name':
            filtered_services = [s for s in services if s.service_name == search_query]
        elif search_type == 'rating':
            if search_query.startswith(">"):
                threshold = float(search_query[1:])
                filtered_services = [s for s in services if s.avg_rating and s.avg_rating > threshold]
            elif "<rating<=" in search_query:
                parts = search_query.split("<rating<=")
                lower = float(parts[0])
                upper = float(parts[1])
                filtered_services = [
                    s for s in services if s.avg_rating and lower < s.avg_rating <= upper
                ]
        elif search_type == 'address':
            filtered_services = [s for s in services if s.address and search_query.lower() in s.address.lower()]
        elif search_type == 'pincode':
            filtered_services = [s for s in services if s.pincode and search_query in s.pincode]

    if request.method == 'POST' and 'service_id' in request.form:
        service_id_to_book = int(request.form.get('service_id'))
        current_status = service_status_map.get(service_id_to_book)

        if current_status == 'Accepted':
            flash("This service is already accepted.", "warning")
        else:
            professional_id = next((s.professional_id for s in services if s.service_id == service_id_to_book), None)
            if professional_id:
                new_request = ServiceRequest(
                    service_id=service_id_to_book,
                    homeowner_id=homeowner_id,
                    professional_id=professional_id,
                    service_status='Pending',
                    service_name=next((s.service_name for s in services if s.service_id == service_id_to_book), None)
                )
                db.session.add(new_request)
                db.session.commit()
                flash("Service successfully booked!", "success")
                service_status_map[service_id_to_book] = 'Pending'

    return render_template(
        'homeowner_search.html', is_homeowner=True,
        search_type=search_type,
        search_options=search_options,
        search_query=search_query,
        filtered_services=filtered_services,
        service_status_map=service_status_map
    )


@app.route('/admin_search', methods=['GET', 'POST'])
def admin_search():
    homeowners = Homeowner.query.join(User, Homeowner.homeowner_id == User.user_id).all()
    professionals = Professional.query.join(User, Professional.professional_id == User.user_id).all()
    search_type_homeowner = request.form.get('search_type_homeowner', 'homeowner_id')
    search_type_professional = request.form.get('search_type_professional', 'professional_id')
    search_query_homeowner = request.form.get('search_query_homeowner')
    search_query_professional = request.form.get('search_query_professional')

    homeowner_options = {
        "homeowner_id": sorted(set([str(h.user.user_id) for h in homeowners])),
        "username": sorted(set([h.user.username for h in homeowners])),
        "address": sorted(set([h.user.address for h in homeowners])),
        "pincode": sorted(set([str(h.user.pincode) for h in homeowners])),
        "email": sorted(set([h.user.email for h in homeowners]))
    }

    professional_options = {
        "professional_id": sorted(set([str(p.user.user_id) for p in professionals])),
        "username": sorted(set([p.user.username for p in professionals])),
        "address": sorted(set([p.user.address for p in professionals])),
        "pincode": sorted(set([str(p.user.pincode) for p in professionals])),
        "email": sorted(set([p.user.email for p in professionals])),
        "service_name": sorted(set([p.service_name for p in professionals])),
        "service_id": sorted(set([str(p.service_id) for p in professionals]))
    }

    filtered_homeowners = homeowners
    if request.method == 'POST' and 'homeowner_search' in request.form:
        if search_query_homeowner:
            if search_type_homeowner == 'homeowner_id':
                filtered_homeowners = [h for h in homeowners if str(h.user.user_id) == search_query_homeowner]
            elif search_type_homeowner == 'username':
                filtered_homeowners = [h for h in homeowners if h.user.username == search_query_homeowner]
            elif search_type_homeowner == 'address':
                filtered_homeowners = [h for h in homeowners if h.user.address == search_query_homeowner]
            elif search_type_homeowner == 'pincode':
                filtered_homeowners = [h for h in homeowners if str(h.user.pincode) == search_query_homeowner]
            elif search_type_homeowner == 'email':
                filtered_homeowners = [h for h in homeowners if h.user.email == search_query_homeowner]

    filtered_professionals = professionals
    if request.method == 'POST' and 'professional_search' in request.form:
        if search_query_professional:
            if search_type_professional == 'professional_id':
                filtered_professionals = [p for p in professionals if str(p.user.user_id) == search_query_professional]
            elif search_type_professional == 'username':
                filtered_professionals = [p for p in professionals if p.user.username == search_query_professional]
            elif search_type_professional == 'address':
                filtered_professionals = [p for p in professionals if p.user.address == search_query_professional]
            elif search_type_professional == 'pincode':
                filtered_professionals = [p for p in professionals if str(p.user.pincode) == search_query_professional]
            elif search_type_professional == 'email':
                filtered_professionals = [p for p in professionals if p.user.email == search_query_professional]
            elif search_type_professional == 'service_name':
                filtered_professionals = [p for p in professionals if p.service_name == search_query_professional]
            elif search_type_professional == 'service_id':
                filtered_professionals = [p for p in professionals if str(p.service_id) == search_query_professional]

    return render_template(
        'admin_search.html',is_admin=True,is_professional=False,is_homeowner=False,
        homeowner_options=homeowner_options,
        professional_options=professional_options,
        search_type_homeowner=search_type_homeowner,
        search_type_professional=search_type_professional,
        filtered_homeowners=filtered_homeowners,
        filtered_professionals=filtered_professionals
    )


@app.route('/admin_summary')
def admin_summary():
    avg_rating = db.session.query(func.avg(ServiceRequest.rating_by_owner)).scalar()
    avg_rating = round(avg_rating, 2) if avg_rating else 0

    request_summary = (
        db.session.query(
            ServiceRequest.service_status, func.count(ServiceRequest.request_id)
        )
        .group_by(ServiceRequest.service_status)
        .all()
    )

    status_labels = [status for status, _ in request_summary]
    status_counts = [count for _, count in request_summary]
    max_count = max(status_counts) if status_counts else 1 
    zipped_data = zip(status_labels, status_counts)  

    return render_template(
        'admin_summary.html',is_admin=True,is_professional=False,is_homeowner=False,
        avg_rating=avg_rating,
        zipped_data=zipped_data,
        max_count=max_count,
    )

@app.route('/professional_summary', methods=['GET'])
def professional_summary():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    professional = Professional.query.filter_by(professional_id=user_id).first()

    if not professional:
        return "Professional not found or unauthorized access", 403

    avg_rating = (
        db.session.query(func.avg(ServiceRequest.rating_by_owner))
        .filter(ServiceRequest.professional_id == professional.professional_id)
        .scalar()
    )
    avg_rating = round(avg_rating, 2) if avg_rating else 0
    request_summary = (
        db.session.query(
            ServiceRequest.service_status, func.count(ServiceRequest.request_id)
        )
        .filter(ServiceRequest.professional_id == professional.professional_id)
        .group_by(ServiceRequest.service_status)
        .all()
    )

    statuses = ["Accepted", "Rejected", "Pending", "Completed"]
    status_counts_dict = {status: count for status, count in request_summary}
    status_data = [(status, status_counts_dict.get(status, 0)) for status in statuses]

    return render_template(
        'professional_summary.html',
        is_professional=True,
        is_admin=False,
        is_homeowner=False,
        avg_rating=avg_rating,
        status_data=status_data
    )


@app.route('/homeowner_summary')
def homeowner_summary():
    homeowner_id = session.get('user_id')
    request_summary = (
        db.session.query(
            ServiceRequest.service_status, func.count(ServiceRequest.request_id)
        )
        .filter(ServiceRequest.homeowner_id == homeowner_id)
        .group_by(ServiceRequest.service_status)
        .all()
    )
    status_labels = [status for status, _ in request_summary]
    status_counts = [count for _, count in request_summary]

    max_count = max(status_counts) if status_counts else 1
    zipped_data = zip(status_labels, status_counts)

    return render_template(
        'homeowner_summary.html',is_homeowner=True,is_professional=False,is_admin=False,
        zipped_data=zipped_data,
        max_count=max_count
    )

if __name__ == "__main__":
    setup()
    app.run(debug=True)
