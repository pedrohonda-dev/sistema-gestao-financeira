"""
FINANCE PRO — Gestão Financeira Empresarial
Projeto educacional em Python, Tkinter e SQLite.
Execute: python gestao_financeira_pro.py
"""
import csv
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path(__file__).with_name("financeiro_pro.db")

# Paleta
BG = "#F3F6FB"
PANEL = "#FFFFFF"
NAV = "#17243A"
NAV_ACTIVE = "#263B5B"
PRIMARY = "#3B70E4"
TEXT = "#1E293B"
MUTED = "#718096"
BORDER = "#E4EAF2"
GREEN = "#16845B"
RED = "#D34B55"
ORANGE = "#C47A16"


def money(value):
    return "R$ " + f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def parse_money(value):
    value = value.strip().replace("R$", "").replace(" ", "")
    if "," in value:
        value = value.replace(".", "").replace(",", ".")
    return float(value)


def db_connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Geral',
            amount REAL NOT NULL,
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'Pendente',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


class FinanceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Finance Pro | Gestão Financeira")
        self.root.geometry("1280x790")
        self.root.minsize(1020, 650)
        self.root.configure(bg=BG)
        self.conn = db_connect()
        self.selected_id = None

        self.setup_style()
        self.build_shell()
        self.show_dashboard()

    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=PANEL, fieldbackground=PANEL,
                        foreground=TEXT, rowheight=34, borderwidth=0,
                        font=("Segoe UI", 10))
        style.configure("Treeview.Heading", background="#EEF2F8", foreground="#526079",
                        font=("Segoe UI", 9, "bold"), relief="flat", padding=(10, 10))
        style.map("Treeview", background=[("selected", "#DCE8FF")],
                  foreground=[("selected", TEXT)])
        style.configure("TCombobox", padding=7)
        style.configure("TEntry", padding=8)

    def build_shell(self):
        self.sidebar = tk.Frame(self.root, bg=NAV, width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=NAV)
        brand.pack(fill="x", padx=22, pady=(25, 32))
        tk.Label(brand, text="◈  FINANCE", bg=NAV, fg="#FFFFFF",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(brand, text="GESTÃO EMPRESARIAL", bg=NAV, fg="#91A4C1",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(5, 0))

        tk.Label(self.sidebar, text="MENU PRINCIPAL", bg=NAV, fg="#8193AE",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=22, pady=(0, 10))
        self.nav_buttons = {}
        for key, title, icon in [
            ("dashboard", "Visão geral", "▦"),
            ("transactions", "Lançamentos", "⇄"),
            ("reports", "Relatórios", "▤"),
        ]:
            b = tk.Button(self.sidebar, text=f"  {icon}    {title}", anchor="w",
                          command=lambda k=key: self.navigate(k), bd=0,
                          bg=NAV, fg="#D5DFEF", activebackground=NAV_ACTIVE,
                          activeforeground="white", font=("Segoe UI", 10, "bold"),
                          padx=15, pady=13, cursor="hand2")
            b.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[key] = b

        bottom = tk.Frame(self.sidebar, bg=NAV)
        bottom.pack(side="bottom", fill="x", padx=20, pady=22)
        tk.Label(bottom, text="Finance Pro • Projeto ADS", bg=NAV, fg="#91A4C1",
                 font=("Segoe UI", 8)).pack(anchor="w")
        tk.Label(bottom, text="Dados armazenados localmente", bg=NAV, fg="#91A4C1",
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(4, 0))

        self.main = tk.Frame(self.root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(self.main, bg=PANEL, height=76)
        self.header.pack(fill="x")
        self.header.pack_propagate(False)
        self.header_title = tk.Label(self.header, text="Visão geral", bg=PANEL, fg=TEXT,
                                     font=("Segoe UI", 18, "bold"))
        self.header_title.pack(side="left", padx=28)
        self.header_date = tk.Label(self.header, text=date.today().strftime("%d/%m/%Y"),
                                    bg=PANEL, fg=MUTED, font=("Segoe UI", 10))
        self.header_date.pack(side="right", padx=28)
        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=26, pady=22)

    def navigate(self, key):
        if key == "dashboard":
            self.show_dashboard()
        elif key == "transactions":
            self.show_transactions()
        elif key == "reports":
            self.show_reports()

    def set_active(self, key, title):
        self.header_title.config(text=title)
        for name, button in self.nav_buttons.items():
            button.config(bg=NAV_ACTIVE if name == key else NAV,
                          fg="white" if name == key else "#D5DFEF")

    def clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def fetch_all(self):
        return self.conn.execute("SELECT * FROM transactions ORDER BY id DESC").fetchall()

    def totals(self):
        rows = self.fetch_all()
        incoming = sum(r["amount"] for r in rows if r["kind"] == "Entrada" and r["status"] == "Concluído")
        outgoing = sum(r["amount"] for r in rows if r["kind"] == "Saída" and r["status"] == "Concluído")
        pending_in = sum(r["amount"] for r in rows if r["kind"] == "Entrada" and r["status"] == "Pendente")
        pending_out = sum(r["amount"] for r in rows if r["kind"] == "Saída" and r["status"] == "Pendente")
        return rows, incoming, outgoing, pending_in, pending_out

    def card(self, parent, title, value, subtitle, accent):
        box = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tk.Frame(box, bg=accent, width=5).pack(side="left", fill="y")
        body = tk.Frame(box, bg=PANEL)
        body.pack(side="left", fill="both", expand=True, padx=17, pady=16)
        tk.Label(body, text=title.upper(), bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(body, text=value, bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(8, 4))
        tk.Label(body, text=subtitle, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        return box

    def section_title(self, parent, title, description=None):
        frame = tk.Frame(parent, bg=BG)
        frame.pack(fill="x", pady=(0, 13))
        tk.Label(frame, text=title, bg=BG, fg=TEXT,
                 font=("Segoe UI", 13, "bold")).pack(anchor="w")
        if description:
            tk.Label(frame, text=description, bg=BG, fg=MUTED,
                     font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 0))
        return frame

    def show_dashboard(self):
        self.clear_content()
        self.set_active("dashboard", "Visão geral")
        rows, incoming, outgoing, pending_in, pending_out = self.totals()

        tk.Label(self.content, text="Olá! Aqui está o resumo financeiro da empresa.",
                 bg=BG, fg=MUTED, font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 18))
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x")
        for i, (title, value, sub, color) in enumerate([
            ("Entradas realizadas", money(incoming), "Valores recebidos", GREEN),
            ("Saídas realizadas", money(outgoing), "Despesas pagas", RED),
            ("Saldo realizado", money(incoming-outgoing), "Entradas menos saídas", PRIMARY),
            ("Em aberto", money(pending_in+pending_out), "Contas pendentes", ORANGE),
        ]):
            c = self.card(cards, title, value, sub, color)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 10, 0))
            cards.columnconfigure(i, weight=1, uniform="cards")

        row = tk.Frame(self.content, bg=BG)
        row.pack(fill="both", expand=True, pady=(24, 0))
        left = tk.Frame(row, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))
        right = tk.Frame(row, bg=PANEL, width=290, highlightbackground=BORDER, highlightthickness=1)
        right.pack(side="left", fill="y")
        right.pack_propagate(False)

        tk.Label(left, text="Movimentações recentes", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(17, 12))
        cols = ("kind", "description", "category", "amount", "status")
        tree = ttk.Treeview(left, columns=cols, show="headings", height=9)
        names = {"kind":"Tipo", "description":"Descrição", "category":"Categoria",
                 "amount":"Valor", "status":"Situação"}
        widths = {"kind":90, "description":210, "category":130, "amount":130, "status":110}
        for col in cols:
            tree.heading(col, text=names[col])
            tree.column(col, width=widths[col], anchor="w" if col in ("description","category") else "center")
        tree.pack(fill="both", expand=True, padx=12, pady=(0, 14))
        for r in rows[:10]:
            tree.insert("", "end", values=(r["kind"], r["description"], r["category"],
                                           money(r["amount"]), r["status"]))

        tk.Label(right, text="Contas em aberto", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=18, pady=(17, 15))
        self.summary_line(right, "A receber", money(pending_in), GREEN)
        self.summary_line(right, "A pagar", money(pending_out), RED)
        tk.Frame(right, bg=BORDER, height=1).pack(fill="x", padx=18, pady=15)
        tk.Label(right, text="Saldo atual", bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", padx=18)
        tk.Label(right, text=money(incoming-outgoing), bg=PANEL, fg=PRIMARY,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=18, pady=(5, 14))
        tk.Button(right, text="+ Novo lançamento", command=self.show_transactions,
                  bg=PRIMARY, fg="white", activebackground="#2F5FC5", activeforeground="white",
                  relief="flat", font=("Segoe UI", 10, "bold"), padx=14, pady=11,
                  cursor="hand2").pack(fill="x", padx=18, pady=(0, 18))

    def summary_line(self, parent, label, value, color):
        line = tk.Frame(parent, bg=PANEL)
        line.pack(fill="x", padx=18, pady=7)
        tk.Label(line, text=label, bg=PANEL, fg=MUTED, font=("Segoe UI", 10)).pack(side="left")
        tk.Label(line, text=value, bg=PANEL, fg=color, font=("Segoe UI", 10, "bold")).pack(side="right")

    def show_transactions(self):
        self.clear_content()
        self.set_active("transactions", "Lançamentos")
        self.selected_id = None
        self.section_title(self.content, "Cadastro e controle",
                           "Registre entradas, saídas, contas a pagar e valores a receber.")

        form = tk.Frame(self.content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        form.pack(fill="x", pady=(0, 18))
        tk.Label(form, text="NOVO LANÇAMENTO", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", padx=17, pady=(15, 8))

        self.v_kind = tk.StringVar(value="Entrada")
        self.v_desc = tk.StringVar()
        self.v_category = tk.StringVar(value="Geral")
        self.v_amount = tk.StringVar()
        self.v_date = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.v_status = tk.StringVar(value="Pendente")
        self.v_notes = tk.StringVar()
        fields = [
            ("Tipo", self.v_kind, ["Entrada", "Saída"], "combo"),
            ("Descrição", self.v_desc, None, "entry"),
            ("Categoria", self.v_category, ["Vendas", "Serviços", "Salários", "Aluguel", "Impostos", "Fornecedores", "Marketing", "Transporte", "Geral"], "combo"),
            ("Valor (R$)", self.v_amount, None, "entry"),
            ("Vencimento (DD/MM/AAAA)", self.v_date, None, "entry"),
            ("Situação", self.v_status, ["Pendente", "Concluído"], "combo"),
        ]
        self.form_widgets = {}
        for idx, (label, var, options, typ) in enumerate(fields):
            r, c = 1 + idx // 3, idx % 3
            cell = tk.Frame(form, bg=PANEL)
            cell.grid(row=r, column=c, sticky="ew", padx=17, pady=7)
            tk.Label(cell, text=label, bg=PANEL, fg=MUTED,
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=(0, 5))
            if typ == "combo":
                widget = ttk.Combobox(cell, textvariable=var, values=options, state="readonly")
            else:
                widget = ttk.Entry(cell, textvariable=var)
            widget.pack(fill="x", ipady=3)
            self.form_widgets[label] = widget
            form.columnconfigure(c, weight=1)
        btns = tk.Frame(form, bg=PANEL)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=17, pady=(9, 16))
        self.save_btn = tk.Button(btns, text="＋  Salvar lançamento", command=self.save_transaction,
                                  bg=PRIMARY, fg="white", activebackground="#2F5FC5",
                                  activeforeground="white", relief="flat", padx=17, pady=9,
                                  font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.save_btn.pack(side="left")
        tk.Button(btns, text="Limpar formulário", command=self.reset_form,
                  bg="#EEF2F8", fg=TEXT, activebackground="#DCE4EF", relief="flat",
                  padx=15, pady=9, font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=8)

        bar = tk.Frame(self.content, bg=BG)
        bar.pack(fill="x", pady=(0, 9))
        tk.Label(bar, text="Lançamentos cadastrados", bg=BG, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(bar, textvariable=self.search_var, width=26)
        search.pack(side="right", padx=(8, 0))
        search.insert(0, "")
        search.bind("<KeyRelease>", lambda e: self.refresh_table())
        self.filter_var = tk.StringVar(value="Todos")
        filt = ttk.Combobox(bar, textvariable=self.filter_var,
                            values=["Todos", "Entrada", "Saída", "Pendente", "Concluído"],
                            state="readonly", width=15)
        filt.pack(side="right")
        filt.bind("<<ComboboxSelected>>", lambda e: self.refresh_table())

        tablebox = tk.Frame(self.content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        tablebox.pack(fill="both", expand=True)
        cols = ("id", "kind", "description", "category", "amount", "due_date", "status")
        self.tree = ttk.Treeview(tablebox, columns=cols, show="headings")
        labels = {"id":"ID", "kind":"Tipo", "description":"Descrição", "category":"Categoria",
                  "amount":"Valor", "due_date":"Vencimento", "status":"Situação"}
        widths = {"id":45, "kind":85, "description":240, "category":135,
                  "amount":125, "due_date":125, "status":115}
        for col in cols:
            self.tree.heading(col, text=labels[col])
            self.tree.column(col, width=widths[col], anchor="w" if col in ("description","category") else "center")
        self.tree.tag_configure("pending", foreground=ORANGE)
        self.tree.pack(fill="both", expand=True, padx=8, pady=8)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        actions = tk.Frame(self.content, bg=BG)
        actions.pack(fill="x", pady=(10, 0))
        tk.Button(actions, text="Editar selecionado", command=self.edit_selected,
                  bg="#E7EEFC", fg=PRIMARY, relief="flat", padx=14, pady=9,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left")
        tk.Button(actions, text="Marcar como concluído", command=self.mark_done,
                  bg="#E4F5EC", fg=GREEN, relief="flat", padx=14, pady=9,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left", padx=8)
        tk.Button(actions, text="Excluir", command=self.delete_selected,
                  bg="#FCE9EA", fg=RED, relief="flat", padx=14, pady=9,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="left")
        tk.Button(actions, text="Exportar CSV", command=self.export_csv,
                  bg="#EEF2F8", fg=TEXT, relief="flat", padx=14, pady=9,
                  font=("Segoe UI", 9, "bold"), cursor="hand2").pack(side="right")
        self.refresh_table()

    def reset_form(self):
        self.selected_id = None
        self.v_kind.set("Entrada")
        self.v_desc.set("")
        self.v_category.set("Geral")
        self.v_amount.set("")
        self.v_date.set(date.today().strftime("%d/%m/%Y"))
        self.v_status.set("Pendente")
        self.save_btn.config(text="＋  Salvar lançamento", command=self.save_transaction)
        if hasattr(self, "tree"):
            for item in self.tree.selection():
                self.tree.selection_remove(item)

    def save_transaction(self):
        self.persist_transaction()

    def persist_transaction(self):
        desc = self.v_desc.get().strip()
        if not desc:
            messagebox.showwarning("Campo obrigatório", "Informe a descrição.")
            return
        try:
            amount = parse_money(self.v_amount.get())
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Valor inválido", "Digite um valor maior que zero, por exemplo 1500,50.")
            return
        date_text = self.v_date.get().strip()
        if date_text:
            try:
                datetime.strptime(date_text, "%d/%m/%Y")
            except ValueError:
                messagebox.showwarning("Data inválida", "Use o formato DD/MM/AAAA.")
                return
        data = (self.v_kind.get(), desc, self.v_category.get().strip() or "Geral",
                amount, date_text, self.v_status.get(), "", date.today().isoformat())
        if self.selected_id:
            self.conn.execute("""UPDATE transactions SET kind=?, description=?, category=?, amount=?,
                due_date=?, status=?, notes=?, created_at=? WHERE id=?""", data + (self.selected_id,))
        else:
            self.conn.execute("""INSERT INTO transactions
                (kind, description, category, amount, due_date, status, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", data)
        self.conn.commit()
        self.reset_form()
        self.refresh_table()
        messagebox.showinfo("Salvo", "Lançamento salvo com sucesso.")

    def refresh_table(self):
        if not hasattr(self, "tree") or not self.tree.winfo_exists():
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        filt = self.filter_var.get()
        query = self.search_var.get().strip().lower()
        for r in self.fetch_all():
            if filt != "Todos" and filt not in (r["kind"], r["status"]):
                continue
            if query and query not in (r["description"] + " " + r["category"]).lower():
                continue
            self.tree.insert("", "end", values=(r["id"], r["kind"], r["description"], r["category"],
                            money(r["amount"]), r["due_date"] or "—", r["status"]),
                            tags=("pending",) if r["status"] == "Pendente" else ())

    def selected_transaction(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Selecione um item", "Selecione um lançamento na tabela.")
            return None
        return int(self.tree.item(selection[0], "values")[0])

    def edit_selected(self):
        tid = self.selected_transaction()
        if tid is None:
            return
        r = self.conn.execute("SELECT * FROM transactions WHERE id=?", (tid,)).fetchone()
        self.selected_id = tid
        self.v_kind.set(r["kind"])
        self.v_desc.set(r["description"])
        self.v_category.set(r["category"])
        self.v_amount.set(str(r["amount"]).replace(".", ","))
        self.v_date.set(r["due_date"] or "")
        self.v_status.set(r["status"])
        self.save_btn.config(text="✓  Atualizar lançamento", command=self.persist_transaction)

    def on_select(self, _event=None):
        pass

    def mark_done(self):
        tid = self.selected_transaction()
        if tid is None:
            return
        self.conn.execute("UPDATE transactions SET status='Concluído' WHERE id=?", (tid,))
        self.conn.commit()
        self.refresh_table()

    def delete_selected(self):
        tid = self.selected_transaction()
        if tid is None:
            return
        if messagebox.askyesno("Confirmar exclusão", "Deseja excluir definitivamente este lançamento?"):
            self.conn.execute("DELETE FROM transactions WHERE id=?", (tid,))
            self.conn.commit()
            self.reset_form()
            self.refresh_table()

    def export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
            filetypes=[("Arquivo CSV", "*.csv")], initialfile="relatorio_financeiro.csv")
        if not path:
            return
        rows = self.fetch_all()
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["ID", "Tipo", "Descrição", "Categoria", "Valor", "Vencimento", "Situação", "Criado em"])
            for r in rows:
                writer.writerow([r["id"], r["kind"], r["description"], r["category"],
                                 f'{r["amount"]:.2f}'.replace(".", ","), r["due_date"],
                                 r["status"], r["created_at"]])
        messagebox.showinfo("Exportação concluída", "Arquivo CSV exportado com sucesso.")

    def show_reports(self):
        self.clear_content()
        self.set_active("reports", "Relatórios")
        rows, incoming, outgoing, pending_in, pending_out = self.totals()
        self.section_title(self.content, "Relatório financeiro",
                           "Visão consolidada dos lançamentos registrados no sistema.")
        cards = tk.Frame(self.content, bg=BG)
        cards.pack(fill="x", pady=(0, 20))
        items = [
            ("Entradas concluídas", money(incoming), "Receitas recebidas", GREEN),
            ("Saídas concluídas", money(outgoing), "Despesas pagas", RED),
            ("Saldo realizado", money(incoming-outgoing), "Resultado realizado", PRIMARY),
            ("A receber", money(pending_in), "Entradas pendentes", ORANGE),
            ("A pagar", money(pending_out), "Saídas pendentes", ORANGE),
        ]
        for i, item in enumerate(items):
            c = self.card(cards, *item)
            c.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            cards.columnconfigure(i, weight=1, uniform="reportcards")

        box = tk.Frame(self.content, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="both", expand=True)
        tk.Label(box, text="Resumo por categoria", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=(18, 12))
        totals = {}
        for r in rows:
            key = (r["kind"], r["category"])
            totals[key] = totals.get(key, 0) + r["amount"]
        tree = ttk.Treeview(box, columns=("kind", "category", "total"), show="headings", height=12)
        for col, title, width in [("kind","Tipo",140), ("category","Categoria",300), ("total","Total lançado",200)]:
            tree.heading(col, text=title)
            tree.column(col, width=width, anchor="w" if col == "category" else "center")
        tree.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        for (kind, category), total in sorted(totals.items()):
            tree.insert("", "end", values=(kind, category, money(total)))
        tk.Button(self.content, text="Exportar relatório em CSV", command=self.export_csv,
                  bg=PRIMARY, fg="white", activebackground="#2F5FC5", activeforeground="white",
                  relief="flat", padx=17, pady=10, font=("Segoe UI", 9, "bold"),
                  cursor="hand2").pack(anchor="e", pady=(12, 0))

    def close(self):
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = FinanceApp(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()
