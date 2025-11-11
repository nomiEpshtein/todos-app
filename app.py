from flask import Flask, render_template, request, redirect, url_for,session,flash,send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import io
from flask import Response
import numpy as np



app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///todos.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = "malki" 
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    purchases = db.relationship('Purchase', backref='user', lazy=True)

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String, nullable=True)
    amount = db.Column(db.Integer, nullable=True)
    price = db.Column(db.Float, nullable=True)
    category = db.Column(db.String, nullable=True)
    date = db.Column(db.Date, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

with app.app_context():
    db.create_all()



# עמוד בית
@app.get("/")
def getHomePage():
    return render_template("index.html")

# עמוד פרופיל
@app.get("/profile")
def getProfile():
    Purchase.query.filter(Purchase.date < datetime(1900, 1, 1).date()).delete()
    db.session.commit()
    db.session.commit()
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('getLogin'))
    
    user = User.query.get(user_id)
    if not user:
        return "User not found"
    
    user_purchases = user.purchases
    return render_template("profile.html", purchases=user_purchases)


@app.get("/register")
def getRegister():
    return render_template("register.html")

@app.post("/register")
def postRegister():
    if session.get('is_demo'):
         flash("-פונקציה זו אינה זמינה במצב הדגמה.הרשם")
    email = request.form.get('email')
    password = request.form.get('password')
    if User.query.filter_by(email=email).first():
      return render_template("error.html")
    new_user = User(email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    session['user_id'] = new_user.id
    session['is_demo'] = False
    return redirect(url_for('getProfile'))


@app.get("/login")
def getLogin():
    if session.get('is_demo'):
        flash("-פונקציה זו אינה זמינה במצב הדגמה.הרשם")
        return redirect('register')
    return render_template("login.html")

@app.post("/login")
def postLogin():
    email = request.form.get('email')
    password = request.form.get('password')
    user = User.query.filter_by(email=email, password=password).first()
    if user:
        session['user_id'] = user.id 
        session['is_demo'] = False 
        return redirect(url_for('getProfile'))
    if not user:
      return render_template("error.html")
   

@app.get("/add")
def getAdd():
    if session.get('is_demo'):
        flash("-פונקציה זו אינה זמינה במצב הדגמה.הרשם")
        return redirect('register')
    if 'user_id' not in session:
        return redirect(url_for('getLogin'))
    return render_template("add.html")


@app.post("/add")
def postAdd():
    if 'user_id' not in session:
        return redirect(url_for('getLogin'))
    product_name = request.form['product_name']
    amount = int(request.form['amount'])
    price = float(request.form['price'])
    category = request.form['category']
    date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()


    new_purchase = Purchase(
        product_name=product_name,
        amount=amount,
        price=price,
        category=category,
        date=date,
        user_id=session['user_id'] 
    )
    db.session.add(new_purchase)
    db.session.commit()
    return redirect(url_for('getProfile'))



@app.route("/logout")
def logout():
    session.clear()
    flash("התנתקת בהצלחה")
    return redirect(url_for("getHomePage"))

@app.post("/profile/show")
def postShow():   
    user_id = session.get('user_id')
    is_demo = session.get('is_demo', False)
    if not user_id and not is_demo:
        return redirect(url_for('getLogin'))
    start_date = request.form.get('start')
    end_date = request.form.get('end')
    category = request.form.get('category')
    
    limit_raw = request.form.get('limit', 5)
    try:
        limit = int(limit_raw)
        if limit <= 0:
            limit = 5
    except (ValueError, TypeError):
        limit = 5

    if is_demo:
        df = pd.DataFrame(session.get('demo_data', []))
        if not df.empty and not np.issubdtype(df['date'].dtype, np.datetime64):
            df['date'] = pd.to_datetime(df['date'])

        if start_date:
            try:
                start_date_dt = pd.to_datetime(start_date)
                df = df[df['date'] >= start_date_dt]
            except ValueError:
                flash("פורמט תאריך התחלה לא חוקי, יתכן והוא יתעלם")
        if end_date:
            try:
                end_date_dt = pd.to_datetime(end_date)
                df = df[df['date'] <= end_date_dt]
            except ValueError:
                flash("פורמט תאריך סיום לא חוקי, יתכן והוא יתעלם")
        if category and category != 'all':
            df = df[df['category'] == category]
        
        total_count = len(df)
        user_purchases = df.sort_values('date', ascending=False).head(limit).to_dict(orient='records')
        show_more = total_count > limit
    else:
        query = Purchase.query.filter_by(user_id=user_id)

        if start_date:
            try:
                start_date_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                query = query.filter(Purchase.date >= start_date_dt)
            except ValueError:
                flash("פורמט תאריך התחלה לא חוקי, יתכן והוא יתעלם")
        if end_date:
            try:
                end_date_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                query = query.filter(Purchase.date <= end_date_dt)
            except ValueError:
                flash("פורמט תאריך סיום לא חוקי, יתכן והוא יתעלם")

        if category and category != 'all':
            query = query.filter(Purchase.category == category)

        total_count = query.count()
        user_purchases = query.order_by(Purchase.date.desc()).limit(limit).all()
        show_more = total_count > limit

    return render_template(
        "profile.html",
        purchases=user_purchases,
        start=start_date,
        end=end_date,
        category=category,
        limit=limit,
        show_more=show_more
    )

#קובץ לגיבוי
@app.get("/saveData")
def saveData():
    if session.get('is_demo'):
        flash("-פונקציה זו אינה זמינה במצב הדגמה.הרשם")
        return redirect('register')
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('getLogin'))
    
    purchases = Purchase.query.filter_by(user_id=user_id).all()

    if not purchases:
      return render_template("error.html")

    data = [
        {
            "product_name": p.product_name,
            "amount": p.amount,
            "price": p.price,
            "category": p.category,
            "date": p.date
        }
        for p in purchases
    ]

    df = pd.DataFrame(data)
     # יצירת קובץ CSV בזיכרון
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")
    csv_buffer.seek(0)

    return send_file(
        io.BytesIO(csv_buffer.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='user_purchases.csv'
    )

@app.get("/graph")
def getGraph():
    if session.get('is_demo'):
        flash("-פונקציה זו אינה זמינה במצב הדגמה.הרשם")
        return redirect('register')
    return render_template("graph.html")
 

#גרפים
@app.post("/graph")
def postGraph():
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('getLogin'))

    purchases = Purchase.query.filter_by(user_id=user_id).all()
    if not purchases:
      return render_template("error.html")

    data = [
        {
            "product_name": p.product_name,
            "amount": p.amount,
            "price": p.price,
            "category": p.category,
            "date": p.date
        }
        for p in purchases
    ]
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'])
    operation = request.form.get('operation', 'sum')
    start_date = request.form.get('start')
    end_date = request.form.get('end')
    chart_type = request.form.get('chart_type', 'bar')
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]

    if df.empty:
        return "לא נמצאו נתונים בטווח המבוקש"

    if operation == 'sum':
        agg = df.groupby('category')['price'].sum()
    elif operation == 'mean':
        agg = df.groupby('category')['price'].mean()
    elif operation == 'count':
        agg = df.groupby('category')['price'].count()
    else:
        agg = df.groupby('category')['price'].sum()
    plt.switch_backend('Agg')
    fig, ax = plt.subplots(figsize=(8,6))
    if chart_type == 'bar':
        agg.plot(kind='bar', ax=ax)
        ax.set_ylabel(operation)
        ax.set_title(f'{operation} לפי קטגוריה')
    elif chart_type == 'pie':
        agg.plot(kind='pie', ax=ax, autopct='%1.1f%%', startangle=90)
        ax.set_ylabel('')
        ax.set_title(f'{operation} לפי קטגוריה')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    return Response(img.getvalue(), mimetype='image/png')
               
@app.get("/demoProfile")
def demoProfile():
    n=10
    product_ids = np.arange(1000, 1000+n)
    product_names = np.array(['מוצר ' + str(i) for i in range(1, n+1)])
    amounts = np.random.randint(1, 5, size=n)
    prices = np.random.randint(10, 200, size=n)
    categories = np.random.choice(['אוכל', 'אלקטרוניקה', 'ביגוד'], size=n)
    dates = pd.date_range(end=pd.Timestamp.today(), periods=n).date
 
    df=pd.DataFrame(
        {
        'product_id': product_ids,
        'product_name': product_names,
        'amount': amounts,
        'price': prices,
        'category': categories,
        'date': dates  
        }
    )
    session['is_demo'] = True
    session['demo_data'] = df.to_dict(orient='records')
    return render_template("profile.html", purchases=df.to_dict(orient='records'))
    



if __name__ == "__main__":
    app.run(debug=True)