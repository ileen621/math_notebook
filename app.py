import os
import sqlite3

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, g,
    abort, session
)
from collections import defaultdict

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'math_notebook.db'),
    )
    os.makedirs(app.instance_path, exist_ok=True)

    def get_db():
        if 'db' not in g:
            g.db = sqlite3.connect(
                app.config['DATABASE'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
        return g.db

    def close_db(e=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()

    app.teardown_appcontext(close_db)

    # 初始化資料表
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                content TEXT NOT NULL
            )
        ''')
        db.commit()

    @app.route('/')
    def index():
        return render_template(
            'index.html',
            hero_title='找尋你的數學靈感',
            hero_subtitle='在這裡捕捉每一次思維的閃光'
        )

    @app.route('/notes')
    def note_list():
        db = get_db()
        q = request.args.get('q', '').strip()

        # 分頁參數
        page_str = request.args.get('page', '1')
        page = int(page_str) if page_str.isdigit() and int(page_str) >= 1 else 1
        per_page = 10

        # 搜尋歷史存 session
        q_history = session.get('q_history', [])
        if q:
            if q not in q_history:
                q_history.insert(0, q)
                session['q_history'] = q_history[:5]

        # 撈出所有符合搜尋 (或全部) 的筆記
        if q:
            pat = f'%{q}%'
            all_notes = db.execute(
                '''SELECT * FROM notes
                   WHERE category LIKE ? OR title LIKE ? OR content LIKE ?
                   ORDER BY id DESC''',
                (pat, pat, pat)
            ).fetchall()
        else:
            all_notes = db.execute(
                'SELECT * FROM notes ORDER BY id DESC'
            ).fetchall()

        # 分頁切割
        total = len(all_notes)
        total_pages = (total + per_page - 1) // per_page
        start = (page - 1) * per_page
        notes = all_notes[start:start + per_page]

        # 如果有搜尋關鍵字，依 category 分組；否則給空 dict
        if q:
            grouped_notes = defaultdict(list)
            for note in all_notes:
                # 只把符合搜尋條件的 note 加進分組
                if q in note['category'] or q in note['title'] or q in note['content']:
                    cat = note['category'] or '未分類'
                    grouped_notes[cat].append(note)
        else:
            grouped_notes = {}

        # 渲染模板時，一定要把 grouped_notes 傳進去
        return render_template(
            'note_list.html',
            notes=notes,
            grouped_notes=grouped_notes,
            q=q,
            q_history=q_history,
            page=page,
            total_pages=total_pages
        )

    @app.route('/note/<int:id>')
    def note_detail(id):
        db = get_db()
        note = db.execute(
            'SELECT * FROM notes WHERE id = ?', (id,)
        ).fetchone()
        if note is None:
            abort(404)
        return render_template('note_detail.html', note=note)

    @app.route('/note/edit', methods=('GET', 'POST'))
    @app.route('/note/edit/<int:id>', methods=('GET', 'POST'))
    def note_edit(id=None):
        db = get_db()
        note = None
        if id is not None:
            note = db.execute(
                'SELECT * FROM notes WHERE id = ?', (id,)
            ).fetchone()
            if note is None:
                flash('找不到該筆記', 'danger')
                return redirect(url_for('note_list'))

        if request.method == 'POST':
            category = request.form['category'].strip()
            title = request.form['title'].strip()
            content = request.form['content'].strip()
            if not category:
                flash('請輸入分類', 'warning')
            elif not title:
                flash('請輸入標題', 'warning')
            elif not content:
                flash('請輸入內容', 'warning')
            else:
                if note:
                    db.execute(
                        'UPDATE notes SET category=?, title=?, content=? WHERE id=?',
                        (category, title, content, id)
                    )
                else:
                    db.execute(
                        'INSERT INTO notes (category, title, content) VALUES (?, ?, ?)',
                        (category, title, content)
                    )
                db.commit()
                return redirect(url_for('note_list'))

        return render_template('note_edit.html', note=note)

    @app.route('/note/delete/<int:id>', methods=('POST',))
    def note_delete(id):
        db = get_db()
        db.execute('DELETE FROM notes WHERE id = ?', (id,))
        db.commit()
        flash('筆記已刪除', 'success')
        return redirect(url_for('note_list'))

    return app

# 直接在 module 層級暴露 app 物件，交由 flask CLI 啟動
app = create_app()
