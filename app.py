import sqlite3, csv, io
from flask import Flask, render_template, request, redirect, session, make_response

app = Flask(__name__)
app.secret_key = 'flowpick_premium_2026_v2'

def get_db():
    # Χρησιμοποιούμε το νέο όνομα βάσης για καθαρό ξεκίνημα
    conn = sqlite3.connect('flowpick_warehouse.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS orders 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  emag_id TEXT, sku TEXT, product_name TEXT, 
                  department TEXT, quantity INTEGER, 
                  appointment TEXT, status TEXT DEFAULT "New", 
                  picker TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'user' not in session:
        session['user'] = 'ADMIN'
    
    user = session['user']
    conn = get_db()
    pickers = conn.execute('SELECT DISTINCT picker FROM orders WHERE picker IS NOT NULL').fetchall()
    
    if user == 'ADMIN':
        res = conn.execute('SELECT * FROM orders ORDER BY status DESC, appointment ASC').fetchall()
    else:
        res = conn.execute('SELECT * FROM orders WHERE picker = ? OR picker IS NULL ORDER BY status DESC, appointment ASC', (user,)).fetchall()
    
    orders_map = {}
    for r in res:
        oid = r['emag_id']
        if oid not in orders_map: 
            orders_map[oid] = {'info': r, 'products': [], 'status': r['status'], 'picker': r['picker']}
        orders_map[oid]['products'].append(r)
    
    conn.close()
    return render_template('index.html', orders=orders_map.values(), user=user, pickers=pickers)

@app.route('/set_user', methods=['POST'])
def set_user():
    val = request.form.get('u')
    if val == 'NEW':
        name = request.form.get('n')
        if name: session['user'] = name.strip().upper()
    else:
        session['user'] = val
    return redirect('/')

@app.route('/upload', methods=['POST'])
def upload():
    f = request.files.get('f')
    if f:
        stream = io.StringIO(f.stream.read().decode("UTF8"))
        reader = csv.DictReader(stream)
        conn = get_db()
        for r in reader:
            conn.execute('''INSERT INTO orders (emag_id, sku, product_name, department, quantity, appointment) 
                            VALUES (?,?,?,?,?,?)''',
                (r.get('Order_ID'), r.get('SKU'), r.get('Title'), r.get('Dept'), r.get('Qty'), r.get('Date')))
        conn.commit()
        conn.close()
    return redirect('/')

@app.route('/take/<oid>')
def take(oid):
    conn = get_db()
    conn.execute('UPDATE orders SET picker = ? WHERE emag_id = ?', (session.get('user'), oid))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/done/<oid>')
def done(oid):
    conn = get_db()
    conn.execute('UPDATE orders SET status = "Done" WHERE emag_id = ?', (oid,))
    conn.commit()
    conn.close()
    return redirect('/')

@app.route('/clear')
def clear():
    conn = get_db()
    conn.execute('DELETE FROM orders WHERE status = "Done"')
    conn.commit()
    conn.close()
    return redirect('/')

# Η ΝΕΑ ΔΙΑΔΡΟΜΗ ΓΙΑ ΤΟ EXPORT
@app.route('/get_my_data')
def export_data_v2():
    conn = get_db()
    cursor = conn.execute('SELECT emag_id, sku, product_name, quantity, picker, status FROM orders')
    rows = cursor.fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Order_ID', 'SKU', 'Product', 'Quantity', 'Picker', 'Status'])
    for r in rows:
        writer.writerow(list(r))
    
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = "attachment; filename=flowpick_report.csv"
    response.headers["Content-type"] = "text/csv"
    return response

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)