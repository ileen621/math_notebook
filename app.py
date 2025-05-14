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
)


def create_app():
    # 建立 Flask 應用，並使用 instance 資料夾儲存資料庫
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(
            app.instance_path,
            'math_notebook.db',
        ),
    )

    # 確保 instance 資料夾存在
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

    def init_db():
        db = get_db()
        db.execute(
            (
                'CREATE TABLE IF NOT EXISTS notes ('
                'id INTEGER PRIMARY KEY AUTOINCREMENT, '
                'title TEXT NOT NULL, '
                'content TEXT NOT NULL'
                ');'
            )
        )
        db.commit()

    # 立即初始化資料庫
    with app.app_context():
        init_db()

    # 首頁路由
    @app.route('/')
    def index():
        return render_template('index.html')

    # 筆記列表
    @app.route('/notes')
    def note_list():
        db = get_db()
        notes = (
            db.execute('SELECT * FROM notes ORDER BY id DESC')
            .fetchall()
        )
        return render_template('note_list.html', notes=notes)

    # 新增與編輯筆記
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
                flash('找不到該筆記', 'error')
                return redirect(url_for('note_list'))

        if request.method == 'POST':
            title = request.form.get('title')
            content = request.form.get('content')
            if not title:
                flash('請輸入標題', 'error')
            elif not content:
                flash('請輸入內容', 'error')
            else:
                if note:
                    db.execute(
                        'UPDATE notes SET title = ?, content = ? WHERE id = ?',
                        (title, content, id),
                    )
                else:
                    db.execute(
                        'INSERT INTO notes (title, content) VALUES (?, ?)',
                        (title, content),
                    )
                db.commit()
                return redirect(url_for('note_list'))

        return render_template('note_edit.html', note=note)

    # 刪除筆記
    @app.route('/note/delete/<int:id>', methods=('POST',))
    def note_delete(id):
        db = get_db()
        db.execute('DELETE FROM notes WHERE id = ?', (id,))
        db.commit()
        flash('筆記已刪除', 'success')
        return redirect(url_for('note_list'))

    return app


if __name__ == '__main__':
    create_app().run(debug=True)
