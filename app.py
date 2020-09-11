import sqlite3
from datetime import datetime
from flask import Flask, render_template, g, request, redirect, url_for

app = Flask(__name__)

DATABASE = './database.db'


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    return render_template('index.html')


def get_total(daily_foods, day_id):
    query = '''
    select s.protein, s.fat, s.carbs, (s.protein + s.fat + s.carbs) as total,
        (s.protein * 4 + s.carbs * 4 + s.fat * 9) as calories
    from
    (
        select sum(protein) as protein, sum(fat) as fat, sum(carbs) as carbs
        from food_items as fi
        join days_food_items as dfi
            on dfi.food_item_id = fi.id and dfi.day_id = ?
    ) as s
    '''
    return query_db(query, [day_id], one=True)


@app.route("/days/<id>")
def days(id):
    day = query_db("select id, day from days where id = ?", [id], one=True)
    all_food = query_db("select id, name from food_items")
    query = '''
        select name, protein, fat, carbs, (protein * 4 + fat * 9 + carbs * 4) as calories
        from food_items as fi
        join days_food_items as dfi
            on dfi.food_item_id = fi.id and dfi.day_id = ?
    '''
    daily_foods = query_db(query, [id])
    res = {
        'id': day['id'],
        'format_date': date_format(day['day']),
        'daily_foods': daily_foods
    }
    total = get_total(daily_foods, id)
    return render_template('day.html', day=res, all_food=all_food, x=total)


@app.route("/add_food_to_day/<day_id>", methods=['POST'])
def add_food_to_day(day_id):
    food_id = request.form['food_item_ids']
    db = get_db()
    cur = db.cursor()
    cur = cur.execute(
        "insert into days_food_items (day_id, food_item_id) values (?, ?)", [day_id, food_id])
    db.commit()
    return redirect(url_for('days', id=day_id))


@app.route("/days/create", methods=['POST'])
def create_day():
    date_str = request.form['new-day']
    db = get_db()
    cur = db.cursor()
    cur = cur.execute("insert into days (day) values (?)", [date_str])
    db.commit()
    return redirect(url_for('home'))


@app.route("/food-items/create", methods=['POST'])
def create_food_item():
    f = request.form
    args = [f['food_name'], f['protein'], f['fat'], f['carbs']]
    db = get_db()
    cur = db.cursor()
    cur = cur.execute(
        "insert into food_items (name, protein, fat, carbs) values (?, ?, ?, ?)", args)
    db.commit()
    return redirect(url_for('add_food_item'))


@app.route("/add_food_item")
def add_food_item():
    food_items = query_db("select * from food_items")
    return render_template('add_food_item.html', food_items=food_items)


def date_format(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%B %e, %Y")


@app.route("/home")
def home():
    days = query_db("select * from days order by day desc")
    res = []
    for day in days:
        obj = {'id': day['id'], 'format_date': date_format(day['day'])}
        res.append(obj)
    return render_template('home.html', days=res)
