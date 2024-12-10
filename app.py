import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///magazyn.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'super_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# panel boczny z magazynami
@app.context_processor
def inject_magazyny():
    magazyny_all = Magazyn.query.all()
    return {'magazyny_sidebar': magazyny_all}


# Model użytkownika z grupą i działem
class Uzytkownik(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa_uzytkownika = db.Column(db.String(100), unique=True, nullable=False)
    haslo = db.Column(db.String(100), nullable=False)
    grupa = db.Column(db.Integer, nullable=False, default=1)  # 1-przeglądanie, 2-zmiana ilości, 3-full
    dzial = db.Column(db.String(100), nullable=True)  # nowa kolumna dział
    stanowisko = db.Column(db.String(100), nullable=True)  # Dodaj tę linię
    brygada = db.Column(db.String(100), nullable=True)


# Model Magazyn
class Magazyn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(100), nullable=False, unique=True)
    produkty = db.relationship('Produkt', backref='magazyn', lazy=True)

# Model Produkt z polem obrazka
class Produkt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nazwa = db.Column(db.String(100), nullable=False)
    ilosc = db.Column(db.Integer, nullable=False)
    magazyn_id = db.Column(db.Integer, db.ForeignKey('magazyn.id'), nullable=False)
    obrazek = db.Column(db.String(200), nullable=True)
    numer_seryjny = db.Column(db.String(100), nullable=True)
    model = db.Column(db.String(100), nullable=True)
    uwagi = db.Column(db.Text, nullable=True)
    stan_techniczny = db.Column(db.String(100), nullable=True)











@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        haslo = request.form['haslo']
        uzytkownik = Uzytkownik.query.filter_by(nazwa_uzytkownika=nazwa_uzytkownika, haslo=haslo).first()
        if uzytkownik:
            session['user_id'] = uzytkownik.id
            session['username'] = uzytkownik.nazwa_uzytkownika
            session['grupa'] = uzytkownik.grupa
            session['stanowisko'] = uzytkownik.stanowisko
            flash('Zalogowano pomyślnie!', 'success')
            return redirect(url_for('panel_admina') if nazwa_uzytkownika == 'root' else url_for('index'))
        else:
            flash('Niepoprawna nazwa użytkownika lub hasło!', 'danger')
    return render_template('login.html')

@app.route('/admin')
def panel_admina():
    if session.get('username') != 'root' or session.get('grupa') != 3:
        flash('Dostęp zabroniony!', 'danger')
        return redirect(url_for('login'))
    uzytkownicy = Uzytkownik.query.all()
    return render_template('admin.html', uzytkownicy=uzytkownicy)

@app.route('/dodaj_uzytkownika', methods=['POST'])
def dodaj_uzytkownika():
    if session.get('username') != 'root' or session.get('grupa') != 3:
        flash('Dostęp zabroniony!', 'danger')
        return redirect(url_for('login'))
    nazwa_uzytkownika = request.form['nazwa_uzytkownika']
    haslo = request.form['haslo']
    grupa = int(request.form.get('grupa', 1))
    dzial = request.form.get('dzial', None)
    stanowisko = request.form.get('stanowisko', None)
    brygada = request.form.get('brygada', None)

    if Uzytkownik.query.filter_by(nazwa_uzytkownika=nazwa_uzytkownika).first():
        flash('Użytkownik już istnieje!', 'danger')
    else:
        nowy_uzytkownik = Uzytkownik(
            nazwa_uzytkownika=nazwa_uzytkownika,
            haslo=haslo,
            grupa=grupa,
            dzial=dzial,
            stanowisko=stanowisko,
            brygada=brygada
        )
        db.session.add(nowy_uzytkownik)
        db.session.commit()
        flash('Użytkownik dodany!', 'success')
    return redirect(url_for('panel_admina'))



@app.route('/edytuj_uzytkownika/<int:uzytkownik_id>', methods=['GET', 'POST'])
def edytuj_uzytkownika(uzytkownik_id):
    if session.get('username') != 'root' or session.get('grupa') != 3:
        flash('Dostęp zabroniony!', 'danger')
        return redirect(url_for('login'))
    u = Uzytkownik.query.get_or_404(uzytkownik_id)
    if request.method == 'POST':
        u.nazwa_uzytkownika = request.form['nazwa_uzytkownika']
        u.haslo = request.form['haslo']
        u.grupa = int(request.form['grupa'])
        u.dzial = request.form.get('dzial', None)
        u.stanowisko = request.form.get('stanowisko', None)
        u.brygada = request.form.get('brygada', None)
        db.session.commit()
        flash('Użytkownik zaktualizowany!', 'success')
        return redirect(url_for('panel_admina'))
    return render_template('edytuj_uzytkownika.html', uzytkownik=u)


@app.route('/usun_uzytkownika/<int:uzytkownik_id>')
def usun_uzytkownika(uzytkownik_id):
    if session.get('username') != 'root' or session.get('grupa') != 3:
        flash('Dostęp zabroniony!', 'danger')
        return redirect(url_for('login'))
    u = Uzytkownik.query.get_or_404(uzytkownik_id)
    db.session.delete(u)
    db.session.commit()
    flash('Użytkownik usunięty!', 'success')
    return redirect(url_for('panel_admina'))

@app.route('/')
def index():
    if 'user_id' not in session:
        flash('Musisz być zalogowany, aby zobaczyć tę stronę!', 'warning')
        return redirect(url_for('login'))
    magazyny = Magazyn.query.all()
    return render_template('index.html', magazyny=magazyny)

@app.route('/magazyn/<int:magazyn_id>')
def magazyn(magazyn_id):
    if 'user_id' not in session:
        flash('Musisz być zalogowany!', 'warning')
        return redirect(url_for('login'))
    magazyn = Magazyn.query.get_or_404(magazyn_id)
    
    # Pobieramy parametry filtrowania z GET
    f_id = request.args.get('f_id', '').strip()
    f_nazwa = request.args.get('f_nazwa', '').strip()
    f_ilosc = request.args.get('f_ilosc', '').strip()
    f_numer_seryjny = request.args.get('f_numer_seryjny', '').strip()
    f_model = request.args.get('f_model', '').strip()
    f_uwagi = request.args.get('f_uwagi', '').strip()
    f_stan_techniczny = request.args.get('f_stan_techniczny', '').strip()

    query = Produkt.query.filter_by(magazyn_id=magazyn_id)

    # Filtr ID (dokładne dopasowanie)
    if f_id:
        if f_id.isdigit():
            query = query.filter(Produkt.id == int(f_id))
        else:
            # Jeśli f_id nie jest liczbą, filtr nie ma sensu, można pominąć lub dać komunikat
            query = query.filter(Produkt.id == -1)  # żadnych wyników

    # Filtr nazwy (fragment nazwy, case-insensitive)
    if f_nazwa:
        query = query.filter(Produkt.nazwa.ilike(f'%{f_nazwa}%'))

    # Filtr ilości (dokładne dopasowanie)
    if f_ilosc:
        if f_ilosc.isdigit():
            query = query.filter(Produkt.ilosc == int(f_ilosc))
        else:
            # Niepoprawna wartość dla ilości, brak wyników
            query = query.filter(Produkt.id == -1)

    # Filtr numeru seryjnego
    if f_numer_seryjny:
        query = query.filter(Produkt.numer_seryjny.ilike(f'%{f_numer_seryjny}%'))

    # Filtr modelu
    if f_model:
        query = query.filter(Produkt.model.ilike(f'%{f_model}%'))

    # Filtr uwag
    if f_uwagi:
        query = query.filter(Produkt.uwagi.ilike(f'%{f_uwagi}%'))

    # Filtr stanu technicznego
    if f_stan_techniczny and f_stan_techniczny != 'wszystkie':
        query = query.filter(Produkt.stan_techniczny == f_stan_techniczny)

    produkty = query.all()
    
    return render_template('magazyn.html', 
                           magazyn=magazyn, 
                           produkty=produkty,
                           f_id=f_id, 
                           f_nazwa=f_nazwa,
                           f_ilosc=f_ilosc,
                           f_numer_seryjny=f_numer_seryjny,
                           f_model=f_model,
                           f_uwagi=f_uwagi,
                           f_stan_techniczny=f_stan_techniczny)



@app.route('/dodaj_magazyn', methods=['POST'])
def dodaj_magazyn():
    if 'user_id' not in session or session.get('grupa') != 3:
        flash('Brak uprawnień do dodawania magazynów!', 'danger')
        return redirect(url_for('index'))
    nazwa = request.form['nazwa']
    nowy_magazyn = Magazyn(nazwa=nazwa)
    db.session.add(nowy_magazyn)
    db.session.commit()
    flash('Magazyn dodany!', 'success')
    return redirect(url_for('index'))

@app.route('/usun_magazyn/<int:id>')
def usun_magazyn(id):
    if 'user_id' not in session or session.get('grupa') != 3:
        flash('Brak uprawnień do usuwania magazynów!', 'danger')
        return redirect(url_for('index'))
    magazyn = Magazyn.query.get_or_404(id)
    for produkt in magazyn.produkty:
        db.session.delete(produkt)
    db.session.delete(magazyn)
    db.session.commit()
    flash('Magazyn usunięty!', 'success')
    return redirect(url_for('index'))

@app.route('/magazyn/<int:magazyn_id>/dodaj', methods=['POST'])
def dodaj_produkt(magazyn_id):
    if 'user_id' not in session or session.get('grupa') != 3:
        flash('Brak uprawnień do dodawania produktów!', 'danger')
        return redirect(url_for('magazyn', magazyn_id=magazyn_id))
    
    nazwa = request.form['nazwa']
    ilosc = int(request.form['ilosc'])
    numer_seryjny = request.form.get('numer_seryjny', None)
    model = request.form.get('model', None)
    uwagi = request.form.get('uwagi', None)
    stan_techniczny = request.form.get('stan_techniczny', None)
    file = request.files.get('obrazek', None)
    filename = None
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    nowy_produkt = Produkt(
        nazwa=nazwa,
        ilosc=ilosc,
        magazyn_id=magazyn_id,
        obrazek=filename,
        numer_seryjny=numer_seryjny,
        model=model,
        uwagi=uwagi,
        stan_techniczny=stan_techniczny
    )
    db.session.add(nowy_produkt)
    db.session.commit()
    flash('Produkt dodany!', 'success')
    return redirect(url_for('magazyn', magazyn_id=magazyn_id))


@app.route('/usun_produkt/<int:produkt_id>')
def usun_produkt(produkt_id):
    if 'user_id' not in session or session.get('grupa') != 3:
        flash('Brak uprawnień do usuwania produktów!', 'danger')
        return redirect(url_for('index'))
    produkt = Produkt.query.get_or_404(produkt_id)
    magazyn_id = produkt.magazyn_id
    db.session.delete(produkt)
    db.session.commit()
    flash('Produkt usunięty!', 'success')
    return redirect(url_for('magazyn', magazyn_id=magazyn_id))

@app.route('/przenies_produkt/<int:produkt_id>', methods=['GET', 'POST'])
def przenies_produkt(produkt_id):
    if 'user_id' not in session or session.get('grupa') != 3:
        flash('Brak uprawnień do przenoszenia produktów!', 'danger')
        return redirect(url_for('index'))
    
    produkt = Produkt.query.get_or_404(produkt_id)
    magazyny = Magazyn.query.all()  # lista dostępnych magazynów

    if request.method == 'POST':
        nowy_magazyn_id = request.form.get('magazyn_id', None)
        if nowy_magazyn_id and nowy_magazyn_id.isdigit():
            nowy_magazyn_id = int(nowy_magazyn_id)
            # Sprawdź, czy magazyn istnieje
            nowy_magazyn = Magazyn.query.get(nowy_magazyn_id)
            if nowy_magazyn:
                produkt.magazyn_id = nowy_magazyn_id
                db.session.commit()
                flash('Produkt został przeniesiony!', 'success')
                return redirect(url_for('magazyn', magazyn_id=nowy_magazyn_id))
            else:
                flash('Wybrany magazyn nie istnieje!', 'danger')
        else:
            flash('Nie wybrano poprawnego magazynu!', 'danger')

    return render_template('przenies_produkt.html', produkt=produkt, magazyny=magazyny)


@app.route('/edytuj_produkt/<int:produkt_id>', methods=['GET','POST'])
def edytuj_produkt(produkt_id):
    if 'user_id' not in session or session.get('grupa') < 2:
        flash('Brak uprawnień do edycji produktów!', 'danger')
        return redirect(url_for('index'))
    produkt = Produkt.query.get_or_404(produkt_id)
    if request.method == 'POST':
        produkt.ilosc = int(request.form['ilosc'])
        if session.get('grupa') == 3:
            produkt.nazwa = request.form['nazwa']
            produkt.numer_seryjny = request.form.get('numer_seryjny', None)
            produkt.model = request.form.get('model', None)
            produkt.uwagi = request.form.get('uwagi', None)
            produkt.stan_techniczny = request.form.get('stan_techniczny', None)
            file = request.files.get('obrazek', None)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                produkt.obrazek = filename
        db.session.commit()
        flash('Produkt zaktualizowany!', 'success')
        return redirect(url_for('magazyn', magazyn_id=produkt.magazyn_id))
    return render_template('edytuj_produkt.html', produkt=produkt)


@app.route('/obrazek/<filename>')
def obrazek(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/produkt/<int:produkt_id>/obrazek')
def pokaz_obrazek(produkt_id):
    produkt = Produkt.query.get_or_404(produkt_id)
    return render_template('pokaz_obrazek.html', produkt=produkt)

@app.route('/logout')
def logout():
    session.clear()
    flash('Wylogowano!', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Tworzenie konta root
        root_user = Uzytkownik.query.filter_by(nazwa_uzytkownika='root').first()
        if not root_user:
            root = Uzytkownik(nazwa_uzytkownika='root', haslo='root', grupa=3, dzial='Zarząd')
            db.session.add(root)
            db.session.commit()
            print("Konto root zostało utworzone.")
    app.run(debug=True)
