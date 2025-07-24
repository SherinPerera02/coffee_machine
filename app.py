from flask import Flask, render_template, request, redirect, session, url_for
import json
import os

app = Flask(__name__)
app.secret_key = "secret123"

USERS_FILE = 'data/users.json'
RESOURCES_FILE = 'data/resources.json'
SALES_FILE = 'data/sales.json'


def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename) as f:
        return json.load(f)


def save_json(data, filename):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


class CoffeeMachine:
    def __init__(self, resources_file):
        self.resources_file = resources_file
        self.resources = load_json(resources_file)

    def refill(self, water, milk, coffee):
        self.resources['water'] += water
        self.resources['milk'] += milk
        self.resources['coffee'] += coffee
        save_json(self.resources, self.resources_file)


machine = CoffeeMachine(RESOURCES_FILE)

users = load_json(USERS_FILE)


@app.route('/admin')
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect("/login")
    return render_template("admin.html", inventory=machine.resources)


@app.route('/admin/users')
def admin_view_users():
    if not session.get("is_admin"):
        return redirect("/login")
    users = load_json(USERS_FILE)
    return render_template("admin_users.html", users=users)


@app.route('/admin/reports')
def admin_reports():
    if not session.get("is_admin"):
        return redirect("/login")
    sales = load_json(SALES_FILE)
    return render_template("admin_reports.html", sales=sales)


@app.route('/admin/refill', methods=["GET", "POST"])
def admin_refill():
    if not session.get("is_admin"):
        return redirect("/login")
    if request.method == "POST":
        water = int(request.form['water'])
        milk = int(request.form['milk'])
        coffee = int(request.form['coffee'])
        machine.refill(water, milk, coffee)
        return redirect("/admin")
    return render_template("admin_refill.html")


@app.route('/admin/add_user', methods=["GET", "POST"])
def admin_add_user():
    if not session.get("is_admin"):
        return redirect("/login")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        if username in users:
            error = "User already exists."
            return render_template("admin_add_user.html", error=error)
        users[username] = {"password": password, "is_admin": False}
        save_json(users, USERS_FILE)
        return redirect("/admin")
    return render_template("admin_add_user.html")


@app.route('/')
def home():
    if "username" in session:
        return redirect(url_for('menu'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        uname = request.form['username']
        pwd = request.form['password']
        if uname in users and users[uname]['password'] == pwd:
            session['username'] = uname
            session['is_admin'] = users[uname].get('is_admin', False)
            if session['is_admin']:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('menu'))
        return render_template('login.html', error="Invalid credentials")
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        users = load_json(USERS_FILE)
        uname = request.form['username']
        pwd = request.form['password']
        if uname in users:
            return render_template('register.html', error="Username already exists")
        users[uname] = {"password": pwd, "role": "customer", "balance": 0}
        save_json(users, USERS_FILE)
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/menu')
def menu():
    if "username" not in session:
        return redirect(url_for('login'))
    data = load_json(RESOURCES_FILE)
    return render_template('menu.html', drinks=data['menu'])


@app.route('/order/<drink>', methods=['GET', 'POST'])
def order(drink):
    if "username" not in session:
        return redirect(url_for('login'))

    data = load_json(RESOURCES_FILE)
    sales = load_json(SALES_FILE)

    if drink not in data['menu']:
        return "Invalid drink selected", 404

    if request.method == 'POST':
        # payment via notes
        cost = data['menu'][drink]['cost']
        rs20 = int(request.form['rs20'])
        rs50 = int(request.form['rs50'])
        rs100 = int(request.form['rs100'])
        rs500 = int(request.form['rs500'])
        rs1000 = int(request.form['rs1000'])

        total = rs20 * 20 + rs50 * 50 + rs100 * 100 + rs500 * 500 + rs1000 * 1000

        if total < cost:
            return render_template('order.html', drink=drink, error="Not enough money.")

        # check resources
        recipe = data['menu'][drink]
        for item in ['water', 'milk', 'coffee']:
            if data[item] < recipe[item]:
                return render_template('order.html', drink=drink, error=f"Not enough {item}")

        # update stock
        for item in ['water', 'milk', 'coffee']:
            data[item] -= recipe[item]
        sales['total_sales'] += cost
        save_json(data, RESOURCES_FILE)
        save_json(sales, SALES_FILE)

        return render_template('success.html', drink=drink, change=round(total - cost, 2))

    return render_template('order.html', drink=drink)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)
