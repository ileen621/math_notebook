import os
import sqlite3

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    abort,
)


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
                detect_types=sqlite3.PARSE_DECLTYPES,
            )
            g.db.row_factory = sqlite3.Row
        return g.db

    def close_db(error=None):
        db = g.pop('db', None)
        if db is not None:
            db.close()
    app.teardown_appcontext(close_db)

    # 初始化資料表
    def init_db():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                content TEXT NOT NULL
            );
        ''')
        db.commit()
    with app.app_context():
        init_db()

    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/notes')
    def note_list():
        db = get_db()
        q = request.args.get('q', '').strip()
        if q:
            pattern = f'%{q}%'
            notes = db.execute(
                'SELECT * FROM notes '
                'WHERE category LIKE ? OR title LIKE ? OR content LIKE ? '
                'ORDER BY id DESC',
                (pattern, pattern, pattern)
            ).fetchall()
        else:
            notes = db.execute(
                'SELECT * FROM notes ORDER BY id DESC'
            ).fetchall()
        return render_template('note_list.html', notes=notes, q=q)

    @app.route('/note/<int:id>')
    def note_detail(id):
        db = get_db()
        note = db.execute(
            'SELECT * FROM notes WHERE id = ?',
            (id,)
        ).fetchone()
        if note is None:
            abort(404)
        return render_template('note_detail.html', note=note)

    @app.route('/note/edit', methods=('GET','POST'))
    @app.route('/note/edit/<int:id>', methods=('GET','POST'))
    def note_edit(id=None):
        db = get_db()
        note = None
        if id is not None:
            note = db.execute(
                'SELECT * FROM notes WHERE id = ?',
                (id,)
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
                        'UPDATE notes '
                        'SET category=?, title=?, content=? '
                        'WHERE id=?',
                        (category, title, content, id)
                    )
                else:
                    db.execute(
                        'INSERT INTO notes (category, title, content) '
                        'VALUES (?, ?, ?)',
                        (category, title, content)
                    )
                db.commit()
                return redirect(url_for('note_list'))

        return render_template('note_edit.html', note=note)

    @app.route('/note/delete/<int:id>', methods=('POST',))
    def note_delete(id):
        db = get_db()
        db.execute(
            'DELETE FROM notes WHERE id = ?',
            (id,)
        )
        db.commit()
        flash('筆記已刪除', 'success')
        return redirect(url_for('note_list'))

    return app


if __name__ == '__main__':
    create_app().run(debug=True, host='0.0.0.0', port=5000)
