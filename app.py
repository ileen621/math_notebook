import os
import sqlite3
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, g,
    abort, session
)

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-請務必換成更隨機的字串'),
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
                content TEXT NOT NULL,
                doodle_data TEXT DEFAULT '',
                doodle_color TEXT DEFAULT '',
                doodle_brush INTEGER DEFAULT 3
            );
        ''')
        db.commit()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/notes')
    def note_list():
        db = get_db()
        q = request.args.get('q', '').strip()

        # 搜尋歷史
        q_history = session.get('q_history', [])
        if q and q not in q_history:
            q_history.insert(0, q)
            session['q_history'] = q_history[:5]

        # 分頁參數
        page = request.args.get('page', '1')
        page = int(page) if page.isdigit() and int(page) >= 1 else 1
        per_page = 10
        start = (page - 1) * per_page

        params = []
        where_sql = ''
        if q:
            pat = f'%{q}%'
            where_sql = 'WHERE category LIKE ? OR title LIKE ? OR content LIKE ?'
            params = [pat, pat, pat]

        total = db.execute(
            f'SELECT COUNT(*) FROM notes {where_sql}', params
        ).fetchone()[0]
        total_pages = (total + per_page - 1) // per_page

        notes = db.execute(
            f'''
            SELECT * FROM notes
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            ''',
            (*params, per_page, start)
        ).fetchall()

        return render_template(
            'note_list.html',
            notes=notes,
            q=q,
            q_history=q_history,
            page=page,
            total_pages=total_pages
        )

    @app.route('/note/<int:id>')
    def note_detail(id):
        db = get_db()
        note = db.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
        if note is None:
            abort(404)
        return render_template('note_detail.html', note=note)

    @app.route('/note/edit', methods=('GET','POST'))
    @app.route('/note/edit/<int:id>', methods=('GET','POST'))
    def note_edit(id=None):
        db = get_db()
        note = None
        if id is not None:
            note = db.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
            if note is None:
                flash('找不到該筆記', 'danger')
                return redirect(url_for('note_list'))

        if request.method == 'POST':
            category     = request.form['category'].strip()
            title        = request.form['title'].strip()
            content      = request.form['content'].strip()
            doodle_data  = request.form.get('doodle_data','').strip()
            doodle_color = request.form.get('doodle_color','').strip()
            doodle_brush = request.form.get('doodle_brush','').strip() or 3

            if not category:
                flash('請輸入分類', 'warning')
            elif not title:
                flash('請輸入標題', 'warning')
            elif not content:
                flash('請輸入內容', 'warning')
            else:
                if note:
                    db.execute('''
                        UPDATE notes
                        SET category=?, title=?, content=?, doodle_data=?, doodle_color=?, doodle_brush=?
                        WHERE id=?
                    ''', (
                        category, title, content,
                        doodle_data, doodle_color, doodle_brush,
                        id
                    ))
                    flash(f'筆記「{title}」已更新', 'success')
                else:
                    db.execute('''
                        INSERT INTO notes
                        (category, title, content, doodle_data, doodle_color, doodle_brush)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        category, title, content,
                        doodle_data, doodle_color, doodle_brush
                    ))
                    flash(f'筆記「{title}」已新增', 'success')
                db.commit()
                return redirect(url_for('note_list'))

        return render_template('note_edit.html', note=note)

    @app.route('/note/delete/<int:id>', methods=('POST',))
    def note_delete(id):
        db = get_db()
        note = db.execute('SELECT * FROM notes WHERE id = ?', (id,)).fetchone()
        if note is None:
            flash('找不到該筆記，無法刪除', 'danger')
        else:
            session['last_deleted'] = dict(note)
            db.execute('DELETE FROM notes WHERE id = ?', (id,))
            db.commit()
            flash(f'筆記「{note["title"]}」已刪除', 'danger')
        return redirect(url_for('note_list'))

    @app.route('/note/recover', methods=('POST',))
    def note_recover():
        data = session.pop('last_deleted', None)
        if not data:
            flash('沒有可復原的筆記', 'warning')
        else:
            db = get_db()
            db.execute('''
                INSERT INTO notes
                (id, category, title, content, doodle_data, doodle_color, doodle_brush)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['id'],
                data['category'],
                data['title'],
                data['content'],
                data['doodle_data'],
                data['doodle_color'],
                data['doodle_brush']
            ))
            db.commit()
            flash(f'筆記「{data["title"]}」已復原', 'success')
        return redirect(url_for('note_list'))

    return app

if __name__ == '__main__':
    create_app().run(debug=True)
