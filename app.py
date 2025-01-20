from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import pandas as pd
from fuzzywuzzy import fuzz
from collections import Counter
import re
import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Ganti dengan kunci rahasia yang lebih aman

# Setup login manager
login_manager = LoginManager()
login_manager.init_app(app)

# Load data
file_path = 'kerusakan_hp.csv'
data = pd.read_csv(file_path)

# Fungsi untuk membersihkan inputan
def clean_input(gejala):
    cleaned_gejala = re.sub(r'[^a-zA-Z\s]', '', gejala.lower()).strip()
    return cleaned_gejala

# Definisikan User untuk flask_login
class User(UserMixin):
    pass

@login_manager.user_loader
def load_user(user_id):
    user = User()
    user.id = user_id
    return user

@app.route('/')
def index():
    gejala_list = data['If'].unique().tolist()  # Menyediakan daftar gejala untuk autocomplete
    return render_template('index.html', gejala_list=gejala_list)

@app.route('/diagnosis', methods=['POST'])
def diagnosis():
    gejala = clean_input(request.form['gejala'])
    if not gejala.strip():
        return render_template('result.html', gejala='Tidak ada gejala yang dimasukkan.', results=[])

    results = []
    for _, row in data.iterrows():
        similarity = fuzz.token_set_ratio(gejala.lower(), row['If'].lower())
        if similarity > 50:  # Ambang batas kecocokan 50%
            results.append({
                'Jenis Kerusakan': row['Jenis Kerusakan'],
                'Then': row['Then'],
                'Saran Perbaikan': row['Saran Perbaikan'],
                'Akurasi': similarity
            })

    # Urutkan berdasarkan Akurasi tertinggi terlebih dahulu
    results.sort(key=lambda x: x['Akurasi'], reverse=True)

    if not results:
        results.append({
            'Jenis Kerusakan': 'Tidak ditemukan',
            'Then': 'Gejala yang dimasukkan tidak sesuai dengan data.',
            'Saran Perbaikan': 'Silakan coba deskripsikan gejala lebih jelas atau periksa kembali data input.',
            'Akurasi': '0%'
        })

    # Menyimpan riwayat diagnosis dalam sesi
    if 'history' not in session:
        session['history'] = []
    session['history'].append({'gejala': gejala, 'results': results})

    # Ubah 'Akurasi' kembali menjadi string untuk tampil di template
    for result in results:
        result['Akurasi'] = f"{result['Akurasi']}%"

    return render_template('result.html', gejala=gejala, results=results)

@app.route('/stats')
def stats():
    if 'history' not in session:
        return render_template('stats.html', stats={})
    
    # Hitung frekuensi gejala yang dimasukkan
    gejala_counter = Counter(entry['gejala'] for entry in session['history'])
    stats = dict(gejala_counter)
    return render_template('stats.html', stats=stats)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User()
        user.id = request.form['username']
        login_user(user)
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Fitur autocomplete untuk gejala
@app.route('/get_gejala')
def get_gejala():
    gejala_list = data['If'].unique().tolist()
    return jsonify(gejala_list)

# Fitur Rating Diagnosis
@app.route('/submit_rating', methods=['POST'])
@login_required
def submit_rating():
    diagnosis_id = request.form['diagnosis_id']
    rating = request.form['rating']
    # Simpan rating ke database atau file (contoh)
    # Misalnya kita simpan ke file `ratings.csv`
    with open('ratings.csv', 'a') as f:
        f.write(f"{diagnosis_id},{rating},{datetime.datetime.now()}\n")
    return render_template('rating_thank_you.html', rating=rating)

# Fitur Pencarian Berdasarkan Kerusakan
@app.route('/search_by_damage', methods=['GET', 'POST'])
def search_by_damage():
    if request.method == 'POST':
        damage_type = request.form['damage_type']
        matching_data = data[data['Jenis Kerusakan'].str.contains(damage_type, case=False, na=False)]
        return render_template('damage_search_result.html', results=matching_data)
    return render_template('search_by_damage.html')

# Fitur Rekomendasi Berdasarkan Riwayat Pengguna
@app.route('/recommendations')
@login_required
def recommendations():
    if 'history' not in session:
        return render_template('recommendations.html', recommendations=[])

    # Ambil riwayat gejala terakhir
    recent_gejala = session['history'][-1]['gejala']
    recommendations = data[data['If'].str.contains(recent_gejala, case=False, na=False)]
    
    return render_template('recommendations.html', recommendations=recommendations)

# Fitur Pengingat untuk Pemeliharaan
@app.route('/maintenance_reminder')
def maintenance_reminder():
    # Menyediakan pengingat setiap kali aplikasi dijalankan
    return render_template('maintenance_reminder.html')

if __name__ == '__main__':
    app.run(debug=True)
