
import os
import json
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, Response, abort
)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user,
    logout_user, login_required, current_user
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func


app = Flask(__name__)


import os

SECRET_KEY = os.environ.get("SECRET_KEY")

if not SECRET_KEY:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "Configure a variável de ambiente SECRET_KEY antes de iniciar."
        )
    SECRET_KEY = "chave-local-apenas-desenvolvimento"

app.config["SECRET_KEY"] = SECRET_KEY


database_url = os.environ.get(
    "DATABASE_URL", "sqlite:///financeiro_web.db"
)

if database_url.startswith("postgres://"):
    database_url = database_url.replace(
        "postgres://", "postgresql://", 1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(
        db.String(180), unique=True, nullable=False, index=True
    )
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    kind = db.Column(db.String(20), nullable=False)
    description = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Pago")
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("user.id"), nullable=False, index=True
    )
    transaction_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(30), nullable=False)
    details = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False
    )


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def record_history(action, transaction, details):
    db.session.add(AuditLog(
        user_id=current_user.id,
        transaction_id=transaction.id if transaction else None,
        action=action,
        details=json.dumps(
            details, ensure_ascii=False, default=str
        )
    ))


def get_owned_transaction(transaction_id):
    transaction = db.session.get(Transaction, transaction_id)

    if transaction is None or transaction.user_id != current_user.id:
        abort(404)

    return transaction


def parse_amount(value):
    value = (value or "").strip().replace("R$", "").replace(" ", "")

    if "," in value:
        value = value.replace(".", "").replace(",", ".")

    try:
        amount = Decimal(value)
    except InvalidOperation:
        raise ValueError("Digite um valor válido.")

    if (
        not amount.is_finite()
        or amount <= 0
        or amount > Decimal("9999999999.99")
    ):
        raise ValueError("O valor deve ser maior que zero.")

    return amount.quantize(Decimal("0.01"))


def read_transaction_form():
    kind = request.form.get("kind", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "").strip()
    status = request.form.get("status", "").strip()
    notes = request.form.get("notes", "").strip()
    date_value = request.form.get("due_date", "").strip()

    if kind not in ("receita", "despesa"):
        raise ValueError("Selecione receita ou despesa.")

    if not description or len(description) > 180:
        raise ValueError("Informe uma descrição de até 180 caracteres.")

    if not category or len(category) > 100:
        raise ValueError("Informe uma categoria de até 100 caracteres.")

    if status not in ("Pago", "Pendente"):
        raise ValueError("Selecione um status válido.")

    amount = parse_amount(request.form.get("amount"))

    due_date = None
    if date_value:
        try:
            due_date = datetime.strptime(
                date_value, "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValueError("A data informada é inválida.")

    return {
        "kind": kind,
        "description": description,
        "category": category,
        "amount": amount,
        "due_date": due_date,
        "status": status,
        "notes": notes[:2000],
    }


def transaction_snapshot(transaction):
    return {
        "tipo": transaction.kind,
        "descricao": transaction.description,
        "categoria": transaction.category,
        "valor": str(transaction.amount),
        "vencimento": str(transaction.due_date or ""),
        "status": transaction.status,
        "observacoes": transaction.notes or "",
    }


@app.route("/")
@login_required
def index():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.created_at.desc()).all()

    receita = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(
        user_id=current_user.id,
        kind="receita",
        status="Pago"
    ).scalar()

    despesa = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter_by(
        user_id=current_user.id,
        kind="despesa",
        status="Pago"
    ).scalar()

    pendentes = Transaction.query.filter_by(
        user_id=current_user.id,
        status="Pendente"
    ).count()

    saldo = Decimal(str(receita)) - Decimal(str(despesa))

    return render_template(
        "index.html",
        transactions=transactions,
        receita=receita,
        despesa=despesa,
        saldo=saldo,
        pendentes=pendentes,
        hoje=datetime.now().date(),
        page="dashboard"
    )


@app.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or len(name) > 100:
            flash("Informe seu nome.", "error")

        elif "@" not in email or len(email) > 180:
            flash("Informe um e-mail válido.", "error")

        elif len(password) < 8:
            flash("A senha precisa ter pelo menos 8 caracteres.", "error")

        elif User.query.filter_by(email=email).first():
            flash("Este e-mail já está cadastrado.", "error")

        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password)
            )

            db.session.add(user)
            db.session.commit()
            login_user(user)

            flash("Conta criada com sucesso!", "success")
            return redirect(url_for("index"))

    return render_template("index.html", page="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(
            user.password_hash, password
        ):
            login_user(user)
            return redirect(url_for("index"))

        flash("E-mail ou senha incorretos.", "error")

    return render_template("index.html", page="login")


@app.route("/sair", methods=["POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/lancamento", methods=["POST"])
@login_required
def create_transaction():
    try:
        data = read_transaction_form()
        transaction = Transaction(
            user_id=current_user.id, **data
        )

        db.session.add(transaction)
        db.session.flush()

        record_history(
            "Criado", transaction,
            transaction_snapshot(transaction)
        )

        db.session.commit()
        flash("Lançamento salvo com sucesso!", "success")

    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")

    return redirect(url_for("index"))


@app.route(
    "/lancamento/<int:transaction_id>/editar",
    methods=["POST"]
)
@login_required
def edit_transaction(transaction_id):
    transaction = get_owned_transaction(transaction_id)
    before = transaction_snapshot(transaction)

    try:
        data = read_transaction_form()

        for key, value in data.items():
            setattr(transaction, key, value)

        record_history(
            "Editado", transaction,
            {
                "antes": before,
                "depois": transaction_snapshot(transaction)
            }
        )

        db.session.commit()
        flash("Lançamento atualizado!", "success")

    except ValueError as error:
        db.session.rollback()
        flash(str(error), "error")

    return redirect(url_for("index"))


@app.route(
    "/lancamento/<int:transaction_id>/excluir",
    methods=["POST"]
)
@login_required
def delete_transaction(transaction_id):
    transaction = get_owned_transaction(transaction_id)
    snapshot = transaction_snapshot(transaction)

    record_history("Excluído", transaction, snapshot)
    db.session.delete(transaction)
    db.session.commit()

    flash("Lançamento excluído.", "success")
    return redirect(url_for("index"))


@app.route("/historico")
@login_required
def history():
    logs = AuditLog.query.filter_by(
        user_id=current_user.id
    ).order_by(AuditLog.created_at.desc()).limit(300).all()

    return render_template(
        "index.html", page="history", logs=logs
    )


@app.route("/exportar.csv")
@login_required
def export_csv():
    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).order_by(Transaction.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Tipo", "Descrição", "Categoria", "Valor",
        "Vencimento", "Status", "Observações", "Criado em"
    ])

    for item in transactions:
        writer.writerow([
            item.kind,
            item.description,
            item.category,
            str(item.amount),
            item.due_date or "",
            item.status,
            item.notes or "",
            item.created_at.strftime("%d/%m/%Y %H:%M")
        ])

    return Response(
        "\ufeff" + output.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition":
            "attachment; filename=lancamentos.csv"
        }
    )


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)