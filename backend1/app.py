from flask import Flask, request, render_template, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from sqlalchemy import or_
import os
import re
from flask_bcrypt import Bcrypt
from dotenv import load_dotenv


load_dotenv()
app = Flask(__name__, template_folder='templates')

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI

bcrypt = Bcrypt(app)
# server_session=Session(app)
db = SQLAlchemy(app)

class Budgets(db.Model):
    BudgetID: int = db.Column(db.Integer, primary_key=True)
    UserID: int = db.Column(db.Integer, db.ForeignKey('user.UserID'))
    Category: str = db.Column(db.String(50), nullable=False)
    Budget: float = db.Column(db.Float, nullable=False)
    Type: str = db.Column(db.String(10), nullable=False) #Expense or Income
    
    def __repr__(self):
         return f'<Budget>'
    
class User(db.Model):
    UserID: int = db.Column(db.Integer, primary_key=True)
    FirstName: str = db.Column(db.String(50), nullable=False)
    LastName: str = db.Column(db.String(50), nullable=False)
    Email: str = db.Column(db.String(50), nullable=False)
    Password: str = db.Column(db.Text, nullable=False)
    Balance: float = db.Column(db.Float, nullable=False,default=0.0)

    # On Delete Cascade
    transactions = relationship("Transactions", backref="User",cascade="all, delete-orphan", lazy="dynamic")

    def __repr__(self):
         return f'<User>'
    
class Transactions(db.Model):
    TransactionID: int = db.Column(db.Integer, primary_key=True)
    UserID: int = db.Column(db.Integer, db.ForeignKey('user.UserID'), nullable=False)
    Amount: float = db.Column(db.Float, nullable=False)
    Category: str = db.Column(db.String(50), nullable=False)
    DateTime: str = db.Column(db.DateTime(timezone=True), nullable=False)
    Description: str = db.Column(db.String(100), nullable=False)
    Type: str = db.Column(db.String(10), nullable=False) #Expense or Income
    
    def __repr__(self):
         return f'<Transactions>'
    
with app.app_context():
    db.create_all()


# Flask Bcrypt
bcrypt = Bcrypt()

# Validate Password


def validate_password(password):

    # Password checker
    # Primary conditions for password validation:
    # Minimum 8 characters.
    # The alphabet must be between [a-z]
    # At least one alphabet should be of Upper Case [A-Z]
    # At least 1 number or digit between [0-9].
    # At least 1 character from [ _ or @ or $ ]. 

    #\s- Returns a match where the string contains a white space character
    if len(password) < 8 or re.search("\s" , password):  
        return False  
    if not (re.search("[a-z]", password) and re.search("[A-Z]", password) and re.search("[0-9]", password) ):
        return False  
    return True  

@app.route('/')
def landingpage():
    loggedIn=False
    if session.get('UserID'):
        loggedIn=True
    return render_template('landingpage.html',loggedIn=loggedIn)

@app.route('/form_login')
def form_login():
    return render_template('login.html')

@app.route('/form_registration')
def form_registration():
    return render_template('registration.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('UserID'):
        return redirect(url_for('form_login'))
    # Getting the user's balance
    user = User.query.filter_by(UserID=session.get('UserID')).first()
    balance = user.Balance
    total_expenses = 0
    total_income = 0
    expenses = Transactions.query.filter_by(UserID=session.get('UserID')).filter_by(Type='Expense')
    for expense in expenses:
        total_expenses += expense.Amount
    incomes = Transactions.query.filter_by(UserID=session.get('UserID')).filter_by(Type='Income')
    for income in incomes:
        total_income += income.Amount

    print(balance)
    # Getting the User's recent 5 transactions
    transactions = Transactions.query.filter_by(UserID=session.get('UserID')).order_by(Transactions.DateTime.desc()).limit(5).all()
    return render_template('dashboard.html',balance=balance, total_expenses=total_expenses, total_income=total_income,transactions=transactions)
    
@app.route('/login',methods=["POST"])
def login():
    # Recieving details of the camp logging in
    email=request.form["email"]
    password=request.form["password"]

    # Checking if the user exists
    user = User.query.filter_by(Email=email).first()
    if user is None:
        flash("Invalid username/password")
        return redirect(url_for('form_login'))

    # Checking if the password matches
    elif not bcrypt.check_password_hash(user.Password,password):
        flash("Invalid username/password")
        return redirect(url_for('form_login'))
    
    else:
        session['UserID'] = user.UserID
        return redirect(url_for('dashboard'))
    
@app.route('/logout')
def logout():
    session.pop('UserID', None)
    return redirect(url_for('landingpage'))

@app.route('/register', methods=['POST','GET'])
def register():
    # Checking if the user is logged in
    if session.get('UserID'):
        return redirect(url_for('dashboard'))
    
    if request.method == 'GET':
        return render_template('registration.html')

    email=request.form["email"]
    password=request.form["password"]
    first_name=request.form["first_name"]
    last_name=request.form["last_name"]
    confirm_password=request.form["confirm_password"]

    if User.query.filter_by(Email=email.strip()).first() is not None:
        return flash("User already exists")
    
    # Checking for empty fields
    if not email and not email.strip():
        flash("Error: Email is mandatory")
        return redirect(url_for('register'))
    elif not first_name and not first_name.strip():
        flash("Error: First name is mandatory")
        return redirect(url_for('register'))
    elif not password and not password.strip():
        flash("Error: Password is mandatory")
        return redirect(url_for('register'))
    elif not confirm_password and not confirm_password.strip():
        flash("Error: Confirm password is mandatory")
        return redirect(url_for('register'))
    elif password != confirm_password:
        flash("Error: Passwords do not match")
        return redirect(url_for('register'))
    
    
    #validating password
    if not password.strip():
        flash("Error: Passwords cannot be empty")
        return redirect(url_for('register'))
    if not validate_password(password): 
        flash("Error: Invaid password pattern.")
        return redirect(url_for('register'))
    
    # Hashing the password
    hashed_password=bcrypt.generate_password_hash(password)

    #add user to database
    new_user =User( FirstName=first_name,
                    Password=hashed_password,
                    LastName=last_name,
                    Email=email,
                )
    db.session.add(new_user)
    db.session.commit()
    flash("Account successfully registered")
    return render_template('login.html')


@app.route('/add_transaction',methods=["POST","GET"])
def add_transaction():
    # Checking if the user is not logged in
    if not session.get('UserID'):
        return redirect(url_for('form_login'))
    
    if request.method == 'GET':
        categories = Budgets.query.filter_by(UserID=session.get('UserID')).all()
        return render_template('addTransaction.html',categories=categories)
    
    amount=request.form["amount"]
    category=request.form["category"]
    description=request.form["description"]
    date=request.form["date"]
    type=Budgets.query.filter_by(Category=category).first().Type

    # Checking for empty fields
    if not amount and not amount.strip():
        flash("Error: Amount is mandatory")
        return redirect(url_for('add_transaction'))
    elif not category and not category.strip():
        flash("Error: Category is mandatory")
        return redirect(url_for('add_transaction'))
    elif not description and not description.strip():
        flash("Error: Description is mandatory")
        return redirect(url_for('add_transaction'))
    elif not date and not date.strip():
        flash("Error: Date is mandatory")
        return redirect(url_for('add_transaction'))
    
    # Adding transaction to database
    new_transaction =Transactions(  Amount=amount,
                                    Category=category,
                                    Description=description,
                                    DateTime=date,
                                    UserID=session.get('UserID'),
                                    Type=type
                                )
    
    user = User.query.filter_by(UserID=session.get('UserID')).first()
    if type == 'Income':
        user.Balance += float(amount)
    elif type == 'Expense':
        user.Balance -= float(amount)

    db.session.add(user)
    db.session.add(new_transaction)
    db.session.commit()
    flash("Transaction successfully added")
    categories = Budgets.query.filter_by(UserID=session.get('UserID')).all()
    return render_template('addTransaction.html',categories=categories)

@app.route('/view_transactions',methods=["POST","GET"])
def view_transactions():
    if request.method == 'GET':
        transactions = Transactions.query.filter_by(UserID=session.get('UserID')).order_by(Transactions.DateTime.desc()).all()
    else:
        # Searching through your transactions
        searchQuery = request.form["searchfield"]
        transactions = Transactions.query.filter_by(UserID=session.get('UserID')).filter(or_(Transactions.Description.like(f'%{searchQuery}%'),Transactions.Category.like(f'%{searchQuery}%'),Transactions.Amount.like(f'%{searchQuery}%'),Transactions.DateTime.like(f'%{searchQuery}%'))).order_by(Transactions.DateTime.desc()).all()
        
    return render_template('transaction.html',transactions=transactions)

@app.route('/delete_transaction/<int:id>')
def delete_transaction(id):
    # IMPLEMENT THIS
    transaction = Transactions.query.get_or_404(id)
    db.session.delete(transaction)
    db.session.commit()
    flash("Transaction successfully deleted")
    return redirect(url_for('view_transactions'))

@app.route('/edit_transaction/<int:id>',methods=["POST","GET"])
def edit_transaction(id):
    pass
    # IMPLEMENT THIS
    # transaction = Transactions.query.get_or_404(id)
    # if request.method == 'GET':
    #     return render_template('editTransaction.html',transaction=transaction)
    
    # amount=request.form["amount"]
    # category=request.form["category"]
    # description=request.form["description"]
    # date=request.form["date"]
    # type=request.form["type"]

    # # Checking for empty fields
    # if not amount and not amount.strip():
    #     flash("Error: Amount is mandatory")
    #     return redirect(url_for('edit_transaction',id=id))
    # elif not category and not category.strip():
    #     flash("Error: Category is mandatory")
    #     return redirect(url_for('edit_transaction',id=id))
    # elif not description and not description.strip():
    #     flash("Error: Description is mandatory")
    #     return redirect(url_for('edit_transaction',id=id))
    # elif not date and not date.strip():
    #     flash("Error: Date is mandatory")
    #     return redirect(url_for('edit_transaction',id=id))
    
    # # Adding transaction to database
    # transaction.Amount=amount
    # transaction.Category=category
    # transaction.Description=description
    # transaction.DateTime=date
    # transaction.Type=type
    # db.session.commit()
    # flash("Transaction successfully edited")
    # return redirect(url_for('view_transactions'))

@app.route('/view_budgets')
def view_budgets():
    # Implement this
    budgets = Budgets.query.filter_by(UserID=session.get('UserID')).all()
    return render_template('view_budgets.html',budgets=budgets)


@app.route('/create_category',methods=["POST","GET"])
def create_category():
    # Creating a category and a budget
    # Checking if the user is not logged in
    if not session.get('UserID'):
        return redirect(url_for('form_login'))
    
    if request.method == 'GET':
        return render_template('create_category.html')
    
    budget=request.form["budget"]
    category=request.form["category"]
    type=request.form["type"]

    # Checking for empty fields
    if not budget and not budget.strip():
        flash("Error: Amount is mandatory")
        return redirect(url_for('create_category'))
    elif not category and not category.strip():
        flash("Error: Category is mandatory")
        return redirect(url_for('create_category'))
    elif not type and not type.strip():
        flash("Error: Type is mandatory")
        return redirect(url_for('create_category'))
    
    # Adding transaction to database
    new_budget =Budgets(Category=category,
                        UserID=session.get('UserID'),
                        Budget=budget,
                        Type=type
                    )
    db.session.add(new_budget)
    db.session.commit()
    flash("Budget successfully created")
    return render_template('create_category.html')

@app.route('/view_categories')
def view_categories():
    categories = Budgets.query.filter_by(UserID=session.get('UserID')).all()
    return render_template('view_categories.html',categories=categories)

@app.route('/edit_category/<int:id>',methods=["POST","GET"])
def edit_category(id):
    category = Budgets.query.get_or_404(id)
    if request.method == 'GET':
        return render_template('edit_category.html',category=category)
    
    budget=request.form["budget"]
    category=request.form["category"]
    type=request.form["type"]

    # Checking for empty fields
    if not budget and not budget.strip():
        flash("Error: Amount is mandatory")
        return redirect(url_for('edit_category',id=id))
    elif not category and not category.strip():
        flash("Error: Category is mandatory")
        return redirect(url_for('edit_category',id=id))
    elif not type and not type.strip():
        flash("Error: Type is mandatory")
        return redirect(url_for('edit_category',id=id))
    
    # Adding transaction to database
    category.Budget=budget
    category.Category=category
    category.Type=type
    db.session.commit()
    flash("Category successfully edited")
    return redirect(url_for('view_categories'))


@app.route('/delete_category/<int:BudgetID>')
def delete_category(BudgetID):
    category = Budgets.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    flash("Category successfully deleted")
    return redirect(url_for('view_categories'))

@app.route('/view_master_table')
def view_master_table():
    categories = Budgets.query.filter_by(UserID=session.get('UserID')).all()
    income_overview = {}
    expense_overview = {}
    # Create a dictionary of categories along with their sums of transactions in each category
    # This algorithm is broken because it adds each one twice.
    # To compensate, the value is halved at the end
    for category in categories:
        if category.Type=="Income":
            incomes = Transactions.query.filter_by(UserID=session.get('UserID')).filter_by(Type="Income").all()
            incomes_structure=[]
            for income in incomes:
                incomes_structure.append({"Amount":income.Amount,"Category":income.Category})
            for income in incomes_structure:
                if income["Category"] not in income_overview:
                    income_overview[income["Category"]]=income["Amount"]
                    print(f"Created new category: income_overview {income['Category']} = {income['Amount']}")
                else:
                    income_overview[income["Category"]]+=income["Amount"]
                    print(f"Added to existing category: income_overview {income['Category']} = {income['Amount']}")
        else:
            expenses = Transactions.query.filter_by(UserID=session.get('UserID')).filter_by(Type="Expense").all()
            expenses_structure=[]
            for expense in expenses:
                expenses_structure.append({"Amount":expense.Amount,"Category":expense.Category})
            for expense in expenses_structure:
                if expense["Category"] not in expense_overview:
                    expense_overview[expense["Category"]]=expense["Amount"]
                    print(f"Created new category: expense_overview {expense['Category']} = {expense['Amount']}")
                else:
                    expense_overview[expense["Category"]]+=expense["Amount"]
                    print(f"Added to existing category: expense_overview {expense['Category']} = {expense['Amount']}")
    
    
    
    income_expectations = {}
    expense_expectations = {}
    for category in categories:
        if category.Type=="Income":
            income_expectations[category.Category]=category.Budget
        else:
            expense_expectations[category.Category]=category.Budget
    total_income_actual =sum(income_overview.values())/2
    total_expense_actual =sum(expense_overview.values())/2
    total_income_plan =sum(income_expectations.values())
    total_expense_plan =sum(expense_expectations.values())
    return render_template('master_table.html',
                           income_overview=income_overview,
                           expense_overview=expense_overview,
                           income_expectations=income_expectations,
                           expense_expectations=expense_expectations,
                           total_income_actual=total_income_actual,
                           total_expense_actual=total_expense_actual,
                           total_income_plan=total_income_plan,
                           total_expense_plan=total_expense_plan
                           )
                
@app.route('/view_notifications')
def view_notifications():
    return render_template('notification.html')
    
if __name__=='__main__':
    app.run(debug=True)