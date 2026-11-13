from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import datetime
import re
import os

app = Flask(__name__)
app.secret_key = 'lzm1024_top_secret'

UPLOAD_FOLDER = 'static/uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id TEXT UNIQUE, username TEXT, password TEXT, role TEXT DEFAULT '普通用户',
                  last_apply_time REAL DEFAULT 0, nickname TEXT, avatar TEXT, bio TEXT DEFAULT '欢迎来到我的个人主页',
                  register_time TEXT, is_applying INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS visitors
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, username TEXT, message TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, sender_id TEXT, receiver_id TEXT, content TEXT, send_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS feedbacks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, content TEXT, create_time TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS announcements
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  content TEXT, 
                  publish_time TEXT)''')
    # 新增：日记表
    c.execute('''CREATE TABLE IF NOT EXISTS diaries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  user_id TEXT, 
                  title TEXT, 
                  content TEXT, 
                  create_time TEXT)''')
                 
    c.execute("SELECT * FROM users WHERE username='lzm1024' AND role='大管理员'")
    if not c.fetchone():
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO users (user_id, username, password, role, register_time) VALUES ('0', 'lzm1024', 'liuzimo1024', '大管理员', ?)", (now_str,))
        
    c.execute("SELECT * FROM users WHERE username='lzm1024' AND role='管理员'")
    if not c.fetchone():
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO users (user_id, username, password, role, register_time) VALUES ('1', 'lzm1024', '123654a.', '管理员', ?)", (now_str,))
    
    conn.commit()
    conn.close()

# ================= 1. 首页 =================
@app.route('/')
def index():
    user = session.get('username')
    user_id = session.get('user_id')
    
    if not user:
        return """
        <div style="text-align:center; margin-top:150px; font-family:sans-serif;">
            <h1 style="font-size:60px; letter-spacing: 5px;">你谁啊</h1>
            <br><br>
            <a href="/dl"><button style="padding:12px 30px; font-size:18px; background:#007bff; color:white; border:none; border-radius:5px; cursor:pointer; margin-right:20px;">登录</button></a>
            <a href="/zc"><button style="padding:12px 30px; font-size:18px; background:#fff; color:#333; border:1px solid #ccc; border-radius:5px; cursor:pointer;">注册</button></a>
        </div>
        """

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("SELECT content, publish_time FROM announcements ORDER BY id DESC LIMIT 1")
    latest_ann = c.fetchone()
    ann_html = ""
    if latest_ann:
        ann_html = f"""
        <div style="background:#fff; border-radius:8px; border:1px solid #eee; padding:20px; margin-bottom:20px; border-left: 4px solid #f0ad4e; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <h3 style="margin-top:0; font-size:16px; color:#f0ad4e; display:flex; align-items:center; gap:8px;">📢 站内公告</h3>
            <p style="font-size:15px; color:#333; line-height:1.6; margin:0;">{latest_ann[0]}</p>
            <div style="font-size:12px; color:#aaa; margin-top:10px; text-align:right;">发布于：{latest_ann[1]}</div>
        </div>
        """
    else:
        ann_html = "<div style='background:#fff; border-radius:8px; border:1px solid #eee; padding:20px; margin-bottom:20px; color:#999; text-align:center;'>暂无公告</div>"

    c.execute("SELECT user_id, username, message FROM visitors ORDER BY id DESC LIMIT 3")
    recent_msgs = c.fetchall()
    
    c.execute("SELECT user_id, nickname, username, role, avatar FROM users WHERE role != '大管理员' ORDER BY id DESC LIMIT 4")
    recent_users = c.fetchall()
    
    c.execute('''SELECT DISTINCT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_id FROM messages WHERE sender_id = ? OR receiver_id = ? LIMIT 3''', (user_id, user_id, user_id))
    recent_chats = c.fetchall()

    c.execute("SELECT id, title, create_time FROM diaries WHERE user_id=? ORDER BY id DESC LIMIT 3", (user_id,))
    recent_diaries = c.fetchall()
    
    forum_html = ""
    for m in recent_msgs:
        m_uid, m_uname, m_text = m
        short_text = m_text[:15] + "..." if len(m_text) > 15 else m_text
        forum_html += f"""
        <div style="padding:8px 0; border-bottom:1px solid #f0f0f0; text-align:left; font-size:13px;">
            <span style="color:#888;">【{m_uid}】<a href="/user/{m_uid}" style="color:#2c7be5; text-decoration:none;">{m_uname}</a>：</span>
            <span style="color:#333;">{short_text}</span>
        </div>
        """
    if not forum_html:
        forum_html = "<p style='color:#999; font-size:13px;'>还没有人留言，快去抢沙发吧！</p>"

    users_html = ""
    for u in recent_users:
        uid, nick, uname, role, avatar = u
        u_nick = nick if nick else uname
        role_color = "#d9534f" if role == '管理员' else "#5cb85c"
        avatar_html = f"<img src='{avatar}' style='width:30px; height:30px; border-radius:50%; object-fit:cover;'>" if avatar else f"<div style='width:30px; height:30px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff; font-size:14px;'>{u_nick[0].upper()}</div>"
        users_html += f"""
        <a href="/user/{uid}" style="text-decoration:none; color:#333; display:flex; justify-content:space-between; align-items:center; padding:6px 0; border-bottom:1px solid #f0f0f0;" onmouseover="this.style.background='#f9f9f9'" onmouseout="this.style.background='#fff'">
            <div style="display:flex; align-items:center; gap:8px;">
                {avatar_html}
                <div><b style="color:#2c7be5; font-size:13px;">{u_nick}</b></div>
            </div>
            <span style="font-size:11px; padding:2px 6px; border-radius:10px; color:#fff; background:{role_color};">{role}</span>
        </a>
        """
    if not users_html:
        users_html = "<p style='color:#999; font-size:13px;'>暂无用户</p>"

    recent_chat_html = ""
    for rc in recent_chats:
        other_id = rc[0]
        c.execute("SELECT nickname, username, avatar FROM users WHERE user_id=?", (other_id,))
        user_info = c.fetchone()
        if user_info:
            nickname = user_info[0] if user_info[0] else user_info[1]
            avatar = user_info[2] if user_info[2] else ""
            avatar_html = f"<img src='{avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;'>" if avatar else f"<div style='width:40px; height:40px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff; font-size:16px;'>{nickname[0].upper()}</div>"
            
            recent_chat_html += f"""
            <a href="/lt/{other_id}" style="text-decoration:none; color:#333; display:flex; align-items:center; gap:10px; padding:8px 0; border-bottom:1px solid #f0f0f0;" onmouseover="this.style.background='#f9f9f9'" onmouseout="this.style.background='#fff'">
                {avatar_html}
                <span style="font-size:13px; color:#2c7be5; font-weight:bold;">{nickname}</span>
            </a>
            """
    if not recent_chat_html:
        recent_chat_html = "<p style='color:#999; font-size:13px;'>暂无聊天记录，快去私信找人聊天吧！</p>"

    diary_html = ""
    for d in recent_diaries:
        diary_html += f"""
        <div style="padding:8px 0; border-bottom:1px solid #f0f0f0; text-align:left; font-size:13px;">
            <a href="/rj/{user_id}/{d[0]}" style="color:#333; text-decoration:none; font-weight:bold;">{d[1]}</a>
            <div style="font-size:11px; color:#aaa; margin-top:2px;">📅 {d[2]}</div>
        </div>
        """
    if not diary_html:
        diary_html = "<p style='color:#999; font-size:13px;'>还没有写过日记，快去记录吧！</p>"

    conn.close()

    nav = f'''
    <div style="text-align: right; padding: 10px 20px; background:#fff; border-bottom:1px solid #ddd;">
        <span>欢迎，<a href="/user/{user_id}" style="color:#2c7be5; text-decoration:none;">{user}</a></span> | 
        <a href="/logout" style="color:#666; text-decoration:none; margin-left:15px;">退出</a>
    </div>
    '''
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>lzm1024 - 首页</title>
        <style>
            body {{ margin:0; background:#f5f5f5; font-family:sans-serif; }}
            .container {{ max-width: 1000px; margin: 30px auto; padding: 0 20px; }}
            .grid-layout {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }}
            .module-card {{ background: #fff; border-radius: 8px; border: 1px solid #eee; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); display: flex; flex-direction: column; height: 220px; }}
            .module-header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #2c7be5; padding-bottom: 8px; margin-bottom: 10px; }}
            .module-title {{ margin: 0; color: #333; font-size: 16px; font-weight: bold; }}
            .module-more {{ text-decoration: none; color: #2c7be5; font-size: 12px; }}
            .module-more:hover {{ text-decoration: underline; }}
            .module-content {{ flex: 1; overflow-y: auto; padding-right: 5px; }}
        </style>
    </head>
    <body>
        {nav}
        <div class="container">
            <div style="grid-column: span 2;">
                {ann_html}
            </div>
            
            <div class="grid-layout">
                <div class="module-card">
                    <div class="module-header"><h3 class="module-title">📝 公共论坛</h3><a href="/gglt" class="module-more">进入 →</a></div>
                    <div class="module-content">{forum_html}</div>
                </div>

                <div class="module-card">
                    <div class="module-header"><h3 class="module-title">👥 活跃用户</h3><a href="/user" class="module-more">查看全部 →</a></div>
                    <div class="module-content">{users_html}</div>
                </div>

                <div class="module-card">
                    <div class="module-header"><h3 class="module-title">💬 最近私信</h3><a href="/lt" class="module-more">进入 →</a></div>
                    <div class="module-content">{recent_chat_html}</div>
                </div>

                <div class="module-card">
                    <div class="module-header"><h3 class="module-title">📔 我的日记</h3><a href="/rj" class="module-more">进入 →</a></div>
                    <div class="module-content">{diary_html}</div>
                </div>
            </div>
        </div>
        <a href="/feedback" style="position:fixed; bottom:40px; right:40px; background:#2c7be5; color:white; padding:12px 24px; border-radius:30px; font-size:16px; font-weight:bold; text-decoration:none; box-shadow:0 4px 12px rgba(44,123,229,0.4); z-index: 999;">✨ 意见反馈</a>
    </body>
    </html>
    """

# ================= 2. 公共论坛 =================
@app.route('/gglt', methods=['GET', 'POST'])
def forum():
    user = session.get('username')
    user_id = session.get('user_id')
    if not user: return redirect(url_for('index'))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    if request.method == 'POST' and 'message' in request.form:
        msg = request.form.get('message')
        if msg:
            c.execute("INSERT INTO visitors (user_id, username, message) VALUES (?, ?, ?)", (user_id, user, msg))
            conn.commit()
            return redirect(url_for('forum'))

    search_text = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    limit = 10
    offset = (page - 1) * limit
    
    base_query = "FROM visitors WHERE 1=1"
    params = []
    if search_text:
        base_query += " AND message LIKE ?"
        params.append(f"%{search_text}%")
        
    c.execute(f"SELECT COUNT(*) {base_query}", params)
    total_records = c.fetchone()[0]
    total_pages = (total_records + limit - 1) // limit 
    if total_pages == 0: total_pages = 1
    
    query = f"SELECT id, user_id, username, message {base_query} ORDER BY id DESC LIMIT ? OFFSET ?"
    c.execute(query, params + [limit, offset])
    messages = c.fetchall()
    conn.close()
    
    msg_html = ""
    for m in messages:
        msg_id, m_user_id, m_username, m_text = m
        msg_html += f"""<div style='background:#fff; padding:15px; margin-bottom:10px; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.05); text-align:left;'><span style='color:#888; font-size:13px;'>【{m_user_id}】<a href="/user/{m_user_id}" style="color:#2c7be5; text-decoration:none; font-weight:bold;">{m_username}</a></span><p style='margin:8px 0 0 0; font-size:15px;'>{m_text}</p></div>"""
    if not msg_html: msg_html = "<p style='color:#999;'>还没有人留言，快来抢沙发！</p>"
    
    page_html = ""
    if total_pages > 1:
        prev_disabled = "disabled" if page <= 1 else ""
        next_disabled = "disabled" if page >= total_pages else ""
        page_html = f"<div style='display:flex; justify-content:center; gap:10px; margin-top:15px;'><a href='?page={page-1}&search={search_text}' style='text-decoration:none; padding:5px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {prev_disabled}'>上一页</a><span style='padding:5px 0;'>第 {page} / {total_pages} 页</span><a href='?page={page+1}&search={search_text}' style='text-decoration:none; padding:5px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {next_disabled}'>下一页</a></div>"
    
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>公共论坛</title>
    <style>
        body {{ margin:0; background:#f5f5f5; font-family:sans-serif; }}
        .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
        .layout {{ display: flex; max-width: 900px; margin: 20px auto; gap: 20px; padding: 0 10px; }}
        .sidebar {{ width: 60px; background: #fff; border-radius: 8px; border: 1px solid #eee; display: flex; flex-direction: column; align-items: center; padding: 10px 0; height: fit-content; }}
        .sidebar-icon {{ display: flex; justify-content: center; align-items: center; width: 40px; height: 40px; margin: 10px 0; border-radius: 8px; color: #666; transition: all 0.2s ease; text-decoration: none; }}
        .sidebar-icon svg {{ width: 22px; height: 22px; }}
        .sidebar-icon:hover {{ color: #2c7be5; background-color: #f0f7ff; }}
        .main-content {{ flex: 1; background:#fff; border-radius: 8px; border: 1px solid #eee; padding: 20px; }}
        .filter-form {{ display:flex; gap:10px; margin-bottom:20px; }}
        .filter-form input[type="text"] {{ padding:8px; border:1px solid #ccc; border-radius:4px; width:100%; }}
        .filter-form button {{ padding:8px 15px; background:#2c7be5; color:white; border:none; border-radius:4px; cursor:pointer; }}
    </style>
    </head>
    <body>
        <div class="top-nav">
            <div><a href="/" style="text-decoration:none; color:#333; font-size:18px; font-weight:bold;">← 返回首页</a></div>
            <div><span>欢迎，<a href="/user/{user_id}" style="color:#2c7be5; text-decoration:none;">{user}</a></span> | <a href="/logout" style="color:#666; text-decoration:none; margin-left:15px;">退出</a></div>
        </div>
        <div class="layout">
            <div class="sidebar">
                <a href="/" title="首页" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></a>
                <a href="/gglt" title="公共论坛" class="sidebar-icon" style="color:#2c7be5; background-color:#f0f7ff;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
                <a href="/user" title="用户列表" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></a>
                <a href="/lt" title="私信" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></a>
                <a href="/rj" title="日记" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
            </div>
            <div class="main-content">
                <h3>📝 发布留言</h3>
                <form method="POST" style="margin-bottom:20px;"><textarea name="message" placeholder="说点什么吧..." required style="width:100%; height:80px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box;"></textarea><button type="submit" style="margin-top:10px; padding:8px 20px; background:#5cb85c; color:white; border:none; border-radius:4px; cursor:pointer;">发送</button></form>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                <h3>🔍 搜索留言</h3>
                <form method="GET" class="filter-form"><input type="text" name="search" value="{search_text}" placeholder="输入关键字..."><button type="submit">搜索</button><a href="/gglt" style="text-decoration:none; color:#666; padding:8px 0;">重置</a></form>
                <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                <h3>💬 最新留言</h3>
                {msg_html}{page_html}
            </div>
        </div>
    </body></html>
    """

# ================= 3. 用户列表 =================
@app.route('/user')
def user_list():
    user = session.get('username')
    user_id = session.get('user_id')
    if not user: return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    page = int(request.args.get('page', 1))
    limit = 15
    offset = (page - 1) * limit
    c.execute("SELECT COUNT(*) FROM users WHERE role != '大管理员'")
    total_users = c.fetchone()[0]
    total_pages = (total_users + limit - 1) // limit
    if total_pages == 0: total_pages = 1
    c.execute("SELECT user_id, nickname, username, role, avatar FROM users WHERE role != '大管理员' ORDER BY id ASC LIMIT ? OFFSET ?", (limit, offset))
    users = c.fetchall()
    conn.close()
    
    user_html = ""
    for u in users:
        uid, nickname, uname, role, avatar = u
        nick = nickname if nickname else uname
        role_color = "#d9534f" if role == '管理员' else "#5cb85c"
        avatar_html = f"<img src='{avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;'>" if avatar else f"<div style='width:40px; height:40px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff; font-size:18px;'>{nick[0].upper()}</div>"
        user_html += f"""<a href="/user/{uid}" class="user-item"><div style="display:flex; align-items:center; gap:15px;">{avatar_html}<div><b style="color:#2c7be5; font-size:16px;">{nick}</b><div style="color:#aaa; font-size:12px; margin-top:2px;">ID: {uid} / 账号: {uname}</div></div></div><span class="role-tag" style="background:{role_color};">{role}</span></a>"""
    if not user_html: user_html = "<p style='text-align:center; color:#999; padding:20px;'>暂无用户。</p>"
    
    page_html = ""
    if total_pages > 1:
        prev_disabled = "disabled" if page <= 1 else ""
        next_disabled = "disabled" if page >= total_pages else ""
        page_html = f"""<div style="display:flex; justify-content:center; align-items:center; gap:15px; margin-top:20px; padding-bottom:20px;"><a href="?page={page-1}" style="text-decoration:none; padding:6px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {prev_disabled}">上一页</a><span style="color:#666; font-size:14px;">第 {page} / {total_pages} 页</span><a href="?page={page+1}" style="text-decoration:none; padding:6px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {next_disabled}">下一页</a></div>"""
    
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>用户列表</title>
    <style>
        body {{ margin:0; background:#f5f5f5; font-family:sans-serif; }}
        .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
        .layout {{ display: flex; max-width: 900px; margin: 20px auto; gap: 20px; padding: 0 10px; }}
        .sidebar {{ width: 60px; background: #fff; border-radius: 8px; border: 1px solid #eee; display: flex; flex-direction: column; align-items: center; padding: 10px 0; height: fit-content; }}
        .sidebar-icon {{ display: flex; justify-content: center; align-items: center; width: 40px; height: 40px; margin: 10px 0; border-radius: 8px; color: #666; transition: all 0.2s ease; text-decoration: none; }}
        .sidebar-icon svg {{ width: 22px; height: 22px; }}
        .sidebar-icon:hover {{ color: #2c7be5; background-color: #f0f7ff; }}
        .main-content {{ flex: 1; background:#fff; border-radius: 8px; border: 1px solid #eee; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
        .header {{ padding:20px; border-bottom:2px solid #2c7be5; display:flex; justify-content:space-between; align-items:center; }}
        .header h2 {{ margin:0; color:#333; }}
        .user-item {{ display:flex; justify-content:space-between; align-items:center; padding:15px 20px; border-bottom:1px solid #f0f0f0; text-decoration:none; color:#333; transition:0.2s; }}
        .user-item:hover {{ background:#f9f9f9; padding-left:25px; }}
        .role-tag {{ font-size:12px; padding:3px 8px; border-radius:12px; color:#fff; }}
    </style>
    </head>
    <body>
        <div class="top-nav">
            <div><a href="/" style="text-decoration:none; color:#333; font-size:18px; font-weight:bold;">← 返回首页</a></div>
            <div><span>欢迎，<a href="/user/{user_id}" style="color:#2c7be5; text-decoration:none;">{user}</a></span> | <a href="/logout" style="color:#666; text-decoration:none; margin-left:15px;">退出</a></div>
        </div>
        <div class="layout">
            <div class="sidebar">
                <a href="/" title="首页" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></a>
                <a href="/gglt" title="公共论坛" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
                <a href="/user" title="用户列表" class="sidebar-icon" style="color:#2c7be5; background-color:#f0f7ff;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></a>
                <a href="/lt" title="私信" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></a>
                <a href="/rj" title="日记" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
            </div>
            <div class="main-content">
                <div class="header"><h2>👥 全站用户列表</h2><span style="color:#888; font-size:14px;">共 {total_users} 人</span></div>
                <div>{user_html}</div>
                {page_html}
            </div>
        </div>
    </body></html>
    """

# ================= 4. 私信列表 & 聊天室 =================
@app.route('/lt')
def chat_list():
    current_id = session.get('user_id')
    if not current_id: return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''SELECT DISTINCT CASE WHEN sender_id = ? THEN receiver_id ELSE sender_id END AS other_id FROM messages WHERE sender_id = ? OR receiver_id = ?''', (current_id, current_id, current_id))
    chat_users = c.fetchall()
    
    chat_html = ""
    for u in chat_users:
        other_id = u[0]
        c.execute("SELECT nickname, username, avatar FROM users WHERE user_id=?", (other_id,))
        user_info = c.fetchone()
        if user_info:
            nickname = user_info[0] if user_info[0] else user_info[1]
            avatar = user_info[2] if user_info[2] else ""
            avatar_html = f"<img src='{avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;'>" if avatar else f"<div style='width:40px; height:40px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff;'>{nickname[0].upper()}</div>"
            
            c.execute('''SELECT content FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY id DESC LIMIT 1''', (current_id, other_id, other_id, current_id))
            last_msg = c.fetchone()
            short_content = (last_msg[0][:12] + "...") if last_msg and len(last_msg[0]) > 12 else (last_msg[0] if last_msg else "")
            
            chat_html += f"""<a href="/lt/{other_id}" style="display:flex; justify-content:space-between; align-items:center; padding:15px 20px; border-bottom:1px solid #f0f0f0; text-decoration:none; color:#333;" onmouseover="this.style.background='#f9f9f9'" onmouseout="this.style.background='#fff'"><div style="display:flex; align-items:center; gap:15px;">{avatar_html}<div style="font-size:16px; font-weight:bold;">{nickname}</div></div><div style="color:#999; font-size:13px; text-align:right; max-width: 50%; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">{short_content}</div></a>"""
    if not chat_html: chat_html = "<p style='text-align:center; color:#999; padding:30px;'>暂无聊天记录，快去用户列表找人聊天吧！</p>"
    conn.close()

    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>我的私信</title>
    <style>
        body {{ margin:0; background:#f5f5f5; font-family:sans-serif; }}
        .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
        .layout {{ display: flex; max-width: 900px; margin: 20px auto; gap: 20px; padding: 0 10px; }}
        .sidebar {{ width: 60px; background: #fff; border-radius: 8px; border: 1px solid #eee; display: flex; flex-direction: column; align-items: center; padding: 10px 0; height: fit-content; }}
        .sidebar-icon {{ display: flex; justify-content: center; align-items: center; width: 40px; height: 40px; margin: 10px 0; border-radius: 8px; color: #666; transition: all 0.2s ease; text-decoration: none; }}
        .sidebar-icon svg {{ width: 22px; height: 22px; }}
        .sidebar-icon:hover {{ color: #2c7be5; background-color: #f0f7ff; }}
        .main-content {{ flex: 1; background:#fff; border-radius: 8px; border: 1px solid #eee; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
        .header {{ padding:20px; border-bottom:1px solid #eee; display:flex; align-items:center; gap:10px; }}
        .header h2 {{ margin:0; color:#333; font-size:18px; }}
    </style>
    </head><body>
        <div class="top-nav">
            <div><a href="/" style="text-decoration:none; color:#333; font-size:18px; font-weight:bold;">← 返回首页</a></div>
            <div><a href="/logout" style="text-decoration:none; color:#666;">退出登录</a></div>
        </div>
        <div class="layout">
            <div class="sidebar">
                <a href="/" title="首页" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></a>
                <a href="/gglt" title="公共论坛" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
                <a href="/user" title="用户列表" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></a>
                <a href="/lt" title="私信" class="sidebar-icon" style="color:#2c7be5; background-color:#f0f7ff;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></a>
                <a href="/rj" title="日记" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
            </div>
            <div class="main-content">
                <div class="header"><svg viewBox="0 0 24 24" fill="none" stroke="#333" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:22px; height:22px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg><h2>私信</h2></div>
                <div>{chat_html}</div>
            </div>
        </div>
    </body></html>
    """

@app.route('/lt/<other_id>', methods=['GET', 'POST'])
def chat_room(other_id):
    current_id = session.get('user_id')
    if not current_id: return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT nickname, username, avatar FROM users WHERE user_id=?", (other_id,))
    other_info = c.fetchone()
    if not other_info:
        conn.close()
        return "该用户不存在"
    other_nickname = other_info[0] if other_info[0] else other_info[1]
    other_avatar = other_info[2] if other_info[2] else ""
    
    c.execute("SELECT nickname, username, avatar FROM users WHERE user_id=?", (current_id,))
    my_info = c.fetchone()
    my_nickname = my_info[0] if my_info[0] else my_info[1]
    my_avatar = my_info[2] if my_info[2] else ""
    
    if request.method == 'POST':
        msg = request.form.get('message')
        if msg:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO messages (sender_id, receiver_id, content, send_time) VALUES (?, ?, ?, ?)", (current_id, other_id, msg, now_str))
            conn.commit()
            return redirect(url_for('chat_room', other_id=other_id))
            
    c.execute('''SELECT sender_id, content, send_time FROM messages WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) ORDER BY id ASC''', (current_id, other_id, other_id, current_id))
    history = c.fetchall()
    conn.close() 
    
    chat_bubbles = ""
    for h in history:
        sender_id, content, send_time = h
        is_me = (sender_id == current_id)
        if is_me:
            avatar_show = f"<img src='{my_avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;'>" if my_avatar else f"<div style='width:40px; height:40px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff; font-size:14px;'>{my_nickname[0].upper()}</div>"
            bubble_style = "display:flex; justify-content:flex-end; margin-bottom:20px; align-items:flex-start; flex-direction:row-reverse; gap:10px;"
            bg_color = "#95ec69"
            msg_align = "text-align: right;"
        else:
            avatar_show = f"<img src='{other_avatar}' style='width:40px; height:40px; border-radius:50%; object-fit:cover;'>" if other_avatar else f"<div style='width:40px; height:40px; border-radius:50%; background:#ccc; display:flex; justify-content:center; align-items:center; color:#fff; font-size:14px;'>{other_nickname[0].upper()}</div>"
            bubble_style = "display:flex; justify-content:flex-start; margin-bottom:20px; align-items:flex-start; gap:10px;"
            bg_color = "#ffffff"
            msg_align = "text-align: left;"
            
        chat_bubbles += f"""
        <div style="{bubble_style}">
            {avatar_show}
            <div style="max-width:65%;">
                <div style="font-size:12px; color:#999; margin-bottom:4px; {msg_align};">{send_time}</div>
                <div style="background:{bg_color}; padding:12px 16px; border-radius:8px; font-size:15px; color:#333; box-shadow:0 1px 3px rgba(0,0,0,0.06); word-break: break-all; text-align: left;">{content}</div>
            </div>
        </div>
        """
        
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>与 {other_nickname} 聊天</title>
    <style>body {{ margin:0; background:#f0f2f5; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}.container {{ max-width:700px; margin:20px auto; background:#ededed; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.08); display:flex; flex-direction:column; height:85vh; overflow:hidden; }}.header {{ padding:15px 20px; background:#fff; border-bottom:1px solid #e0e0e0; display:flex; align-items:center; justify-content:space-between; }}.chat-box {{ flex:1; padding:20px; overflow-y:auto; display:flex; flex-direction:column; }}.input-area {{ padding:15px; background:#fff; border-top:1px solid #e0e0e0; display:flex; gap:10px; }}.input-area input {{ flex:1; padding:12px; border:1px solid #ddd; border-radius:8px; outline:none; font-size:15px; }}.input-area button {{ padding:0 25px; background:#07c160; color:white; border:none; border-radius:8px; cursor:pointer; font-size:15px; font-weight:bold; }}.nav-btn {{ text-decoration:none; color:#333; font-size:24px; display:flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:50%; transition:0.2s; }}.nav-btn:hover {{ background:#f0f0f0; }}.home-btn {{ text-decoration:none; color:#07c160; font-size:14px; padding:8px 16px; border:1px solid #07c160; border-radius:6px; transition:0.2s; }}.home-btn:hover {{ background:#e8f8f0; }}</style>
    </head><body>
        <div class="container">
            <div class="header">
                <div style="display:flex; align-items:center; gap:15px;">
                    <a href="/lt" class="nav-btn" title="返回私信列表">←</a>
                    <h3 style="margin:0; font-size:18px; color:#333;">{other_nickname}</h3>
                </div>
                <a href="/" class="home-btn">返回首页</a>
            </div>
            <div class="chat-box" id="chatBox">{chat_bubbles}</div>
            <form method="POST" class="input-area">
                <input type="text" name="message" placeholder="发消息..." autocomplete="off" required>
                <button type="submit">发送</button>
            </form>
        </div>
        <script>var chatBox = document.getElementById('chatBox'); chatBox.scrollTop = chatBox.scrollHeight;</script>
    </body></html>
    """

# ================= 5. 个人中心 =================
@app.route('/user/<uid>', methods=['GET', 'POST'])
def profile(uid):
    current_user = session.get('username')
    current_role = session.get('role')
    current_id = session.get('user_id')
    if not current_user: return redirect(url_for('index'))
    
    # 核心修复：如果大管理员访问自己的主页，直接送去控制台
    if current_id == '0' and uid == '0':
        return redirect(url_for('admin_console'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    is_owner = (current_id == uid)
    
    # 1. 处理修改个人资料（包含头像上传）
    if request.method == 'POST' and 'update_profile' in request.form and is_owner:
        new_nickname = request.form.get('nickname')
        new_bio = request.form.get('bio')
        new_password = request.form.get('new_password')
        
        file = request.files.get('avatar_file')
        if file and file.filename != '':
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uid}_avatar{ext}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            new_avatar = f"/static/uploads/{filename}"
            c.execute("UPDATE users SET avatar=? WHERE user_id=?", (new_avatar, uid))

        if not new_nickname: new_nickname = current_user 
        c.execute("UPDATE users SET nickname=?, bio=? WHERE user_id=?", (new_nickname, new_bio, uid))
        
        if new_password:
            if len(new_password) < 6 or len(new_password) > 12:
                return "<script>alert('密码长度必须在 6 到 12 位之间！'); history.back();</script>"
            c.execute("UPDATE users SET password=? WHERE user_id=?", (new_password, uid))
            
        conn.commit()
        return redirect(url_for('profile', uid=uid))
        
    # 2. 处理发布留言
    if request.method == 'POST' and 'message' in request.form and is_owner:
        msg = request.form.get('message')
        if msg:
            c.execute("INSERT INTO visitors (user_id, username, message) VALUES (?, ?, ?)", (uid, current_user, msg))
            conn.commit()
            return redirect(url_for('profile', uid=uid))
            
    # 3. 处理管理员发布公告
    if request.method == 'POST' and 'publish_ann' in request.form and current_role in ['管理员', '大管理员']:
        ann_content = request.form.get('ann_content')
        if ann_content:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO announcements (content, publish_time) VALUES (?, ?)", (ann_content, now_str))
            conn.commit()
            return redirect(url_for('profile', uid=uid))

    # 获取目标用户信息
    c.execute("SELECT nickname, username, avatar, bio, register_time, role FROM users WHERE user_id=?", (uid,))
    target_user = c.fetchone()
    
    if not target_user:
        conn.close()
        return "<h1 style='text-align:center; margin-top:100px;'>该用户不存在</h1><a href='/'>返回首页</a>"
        
    # 修复显示名字的核心逻辑
    nickname = target_user[0] if target_user[0] else target_user[1]
    avatar = target_user[2] if target_user[2] else ""
    bio = target_user[3] if target_user[3] else "欢迎来到我的个人主页"
    reg_time = target_user[4] if target_user[4] else "未知"
    target_role = target_user[5]

    # 获取最新公告
    c.execute("SELECT content, publish_time FROM announcements ORDER BY id DESC LIMIT 1")
    latest_ann = c.fetchone()
    ann_html = ""
    if latest_ann:
        ann_html = f"""
        <div class="announcement-card" style="background:#fff; border-radius:8px; border:1px solid #eee; padding:20px; margin-bottom:20px; border-left: 4px solid #f0ad4e;">
            <h3 style="margin-top:0; font-size:15px; color:#f0ad4e;">📢 站内公告</h3>
            <p style="font-size:14px; color:#333; line-height:1.6; margin:0;">{latest_ann[0]}</p>
            <div style="font-size:12px; color:#aaa; margin-top:10px; text-align:right;">{latest_ann[1]}</div>
        </div>
        """
    else:
        ann_html = "<p style='color:#999; text-align:center;'>暂无公告</p>"

    # 获取留言板分页
    search_text = request.args.get('search', '').strip()
    page = int(request.args.get('page', 1))
    limit = 5
    offset = (page - 1) * limit
    
    base_query = "FROM visitors WHERE user_id = ?"
    params = [uid]
    if search_text:
        base_query += " AND message LIKE ?"
        params.append(f"%{search_text}%")
        
    c.execute(f"SELECT COUNT(*) {base_query}", params)
    total_records = c.fetchone()[0]
    total_pages = (total_records + limit - 1) // limit 
    if total_pages == 0: total_pages = 1
    
    query = f"SELECT id, user_id, username, message {base_query} ORDER BY id DESC LIMIT ? OFFSET ?"
    c.execute(query, params + [limit, offset])
    messages = c.fetchall()
    conn.close()
    
    msg_html = ""
    for m in messages:
        msg_id, m_user_id, m_username, m_text = m
        delete_btn = f"<a href='/del_msg/{msg_id}' style='color:#d9534f; font-size:12px; text-decoration:none; margin-left:10px;'>删除</a>" if current_id == m_user_id and is_owner else ""
        msg_html += f"""<div style='background:#fff; padding:10px; margin-bottom:10px; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.05); text-align:left;'><span style='color:#888; font-size:12px;'>【{m_user_id}】<a href="/user/{m_user_id}" style="color:#888; text-decoration:none;">{m_username}</a></span>{delete_btn}<p style='margin:5px 0 0 0;'>{m_text}</p></div>"""
    if not msg_html: msg_html = "<p style='color:#999;'>没有找到留言。</p>"
    
    avatar_html = f"<img src='{avatar}' style='width:100%; height:100%; border-radius:50%; object-fit:cover;'>" if avatar else f"<span style='font-size:24px; color:#fff;'>{nickname[0].upper()}</span>"
    
    page_html = ""
    if total_pages > 1:
        prev_disabled = "disabled" if page <= 1 else ""
        next_disabled = "disabled" if page >= total_pages else ""
        page_html = f"<div style='display:flex; justify-content:center; gap:10px; margin-top:15px;'><a href='?page={page-1}&search={search_text}' style='text-decoration:none; padding:5px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {prev_disabled}'>上一页</a><span style='padding:5px 0;'>第 {page} / {total_pages} 页</span><a href='?page={page+1}&search={search_text}' style='text-decoration:none; padding:5px 15px; background:#fff; border:1px solid #ddd; border-radius:4px; color:#333; {next_disabled}'>下一页</a></div>"
        
    settings_btn = f'<button onclick="openEditModal()" style="padding:8px 12px; background:#fff; border:1px solid #ddd; border-radius:4px; cursor:pointer; width:100%;">个人设置</button>' if is_owner else ''
    admin_console_btn = '<a href="/admin" style="display:block; text-align:center; padding:8px 12px; background:#d9534f; color:white; text-decoration:none; border-radius:4px; font-size:13px;">管理控制台</a>' if current_role == '大管理员' and is_owner else ''
    chat_btn = f'<a href="/lt/{uid}" style="display:block; text-align:center; padding:8px 12px; background:#07c160; color:white; text-decoration:none; border-radius:4px; font-size:13px;">发私信</a>' if not is_owner else ''
    
    post_msg_form = f"""<h3>📝 发布留言</h3><form method="POST"><textarea name="message" placeholder="写点什么吧..." required style="width:100%; height:80px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; margin-bottom:10px; resize:vertical;"></textarea><button type="submit" style="padding: 8px 20px; background: #5cb85c; color: white; border: none; border-radius: 4px; cursor: pointer;">发送</button></form><hr style="border:0; border-top:1px solid #eee; margin:20px 0;">""" if is_owner else ''
    
    edit_modal = f"""<div id="editModal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.4); justify-content:center; align-items:center; z-index:1000;"><div style="background:white; padding:30px; border-radius:8px; box-shadow:0 4px 12px rgba(0,0,0,0.15); text-align:left; width:350px; font-family:sans-serif;"><h3 style="margin-top:0; text-align:center;">修改个人资料</h3><form method="POST" enctype="multipart/form-data"><input type="hidden" name="update_profile" value="1"><label style="font-size:14px; color:#666;">用户名 (展示用，可重复)</label><input type="text" name="nickname" value="{nickname}" placeholder="输入新昵称"><label style="font-size:14px; color:#666;">个性标签</label><input type="text" name="bio" value="{bio}" placeholder="欢迎来到我的个人主页"><label style="font-size:14px; color:#666;">上传新头像 (支持电脑/手机)</label><input type="file" name="avatar_file" accept="image/*" style="margin-bottom:15px;"><label style="font-size:14px; color:#666;">修改密码 (留空则不修改)</label><input type="password" name="new_password" placeholder="输入新密码"><button type="submit" style="margin-top:10px; width:100%; padding:10px 0; background-color:#007bff; color:white; border:none; border-radius:4px;">保存修改</button><button type="button" onclick="document.getElementById('editModal').style.display='none'" style="background:#ccc; margin-top:5px; width:100%; padding:10px 0; border:none; border-radius:4px;">取消</button></form></div></div>""" if is_owner else ''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{nickname} - 个人中心</title>
        <style>
            body {{ margin: 0; background-color: #f5f5f5; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }}
            .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
            .layout {{ display: flex; max-width: 1200px; margin: 20px auto; gap: 20px; padding: 0 10px; }}
            .sidebar {{ width: 60px; background: #fff; border-radius: 8px; border: 1px solid #eee; display: flex; flex-direction: column; align-items: center; padding: 10px 0; height: fit-content; }}
            .sidebar-icon {{ display: flex; justify-content: center; align-items: center; width: 40px; height: 40px; margin: 10px 0; border-radius: 8px; color: #666; transition: all 0.2s ease; text-decoration: none; }}
            .sidebar-icon svg {{ width: 22px; height: 22px; }}
            .sidebar-icon:hover {{ color: #2c7be5; background-color: #f0f7ff; }}
            .main-content {{ flex: 1; }}
            .profile-header {{ background: #fff; border-radius: 8px; border: 1px solid #eee; overflow: hidden; margin-bottom: 20px; position: relative; }}
            .banner {{ height: 150px; background: #e0f7fa; }}
            .avatar-area {{ padding: 20px; display: flex; align-items: center; gap: 15px; margin-top: -40px; }}
            .avatar {{ width: 80px; height: 80px; border-radius: 50%; background: #ccc; border: 3px solid #fff; z-index: 10; display: flex; justify-content: center; align-items: center; overflow: hidden; }}
            .user-info h2 {{ margin: 0 0 5px 0; font-size: 20px; }}
            .user-info p {{ margin: 0; color: #888; font-size: 13px; }}
            .card {{ background: #fff; border-radius: 8px; border: 1px solid #eee; padding: 20px; }}
            .filter-form {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
            .filter-form input[type="text"] {{ padding: 8px; border: 1px solid #ccc; border-radius: 4px; }}
            .filter-form button {{ padding: 8px 15px; background: #2c7be5; color: white; border: none; border-radius: 4px; cursor: pointer; }}
            .right-sidebar {{ width: 300px; }}
            .info-card {{ background: #fff; border-radius: 8px; border: 1px solid #eee; padding: 20px; }}
            .info-item {{ display: flex; justify-content: space-between; margin-bottom: 15px; font-size: 14px; }}
            .info-item span:first-child {{ color: #888; }}
            .modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); justify-content: center; align-items: center; z-index: 1000; }}
            .modal-box {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-align: left; width: 350px; font-family: sans-serif; }}
            .modal-box input {{ width: 100%; padding: 8px; margin-bottom: 15px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
            .modal-box button {{ width: 100%; padding: 10px 0; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }}
        </style>
        <script>function openEditModal() {{ document.getElementById('editModal').style.display = 'flex'; }}</script>
    </head>
    <body>
        <div class="top-nav">
            <b>{nickname} - 个人中心</b>
            <div><a href="/" style="text-decoration:none; color:#666; margin-right:15px;">返回首页</a><a href="/logout" style="text-decoration:none; color:#666;">退出登录</a></div>
        </div>
        
        <div class="layout">
            <div class="sidebar">
                <a href="/" title="首页" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg></a>
                <a href="/gglt" title="公共论坛" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
                <a href="/user" title="用户列表" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg></a>
                <a href="/lt" title="私信" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg></a>
                <a href="/rj" title="日记" class="sidebar-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path></svg></a>
            </div>
            
            <div class="main-content">
                <div class="profile-header">
                    <div class="banner"></div>
                    <div class="avatar-area">
                        <div class="avatar">{avatar_html}</div>
                        <div class="user-info">
                            <h2>{nickname}</h2>
                            <p>{bio}</p>
                        </div>
                    </div>
                </div>

                <div class="card">
                    {post_msg_form}
                    <h3>🔍 筛选 {nickname} 的留言</h3>
                    <form method="GET" class="filter-form">
                        <input type="text" name="search" value="{search_text}" placeholder="搜索内容...">
                        <button type="submit">应用</button>
                        <a href="/user/{uid}" style="text-decoration:none; color:#666; padding:8px 0;">重置</a>
                    </form>
                    <hr style="border:0; border-top:1px solid #eee; margin:20px 0;">
                    <h3>💬 留言板</h3>
                    {msg_html}{page_html}
                </div>
            </div>
            
            <div class="right-sidebar">
                {ann_html}
                
                {f'''
                <div style="background:#fff; border-radius:8px; border:1px solid #eee; padding:15px; margin-bottom:20px;">
                    <h3 style="margin-top:0; font-size:15px; color:#333;">📢 发布新公告</h3>
                    <form method="POST">
                        <input type="hidden" name="publish_ann" value="1">
                        <textarea name="ann_content" placeholder="输入公告内容..." required style="width:100%; height:80px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; resize:vertical; margin-bottom:10px; font-size:13px;"></textarea>
                        <button type="submit" style="width:100%; padding:8px 0; background:#f0ad4e; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">发布公告</button>
                    </form>
                </div>
                ''' if current_role in ['管理员', '大管理员'] and is_owner else ''}
                
                <div style="background:#fff; border-radius:8px; border:1px solid #eee; padding:15px; margin-bottom:20px; display:flex; flex-direction:column; gap:10px;">
                    {settings_btn}
                    {admin_console_btn}
                    {chat_btn}
                    {f'<a href="/rj" style="display:block; text-align:center; padding:8px 12px; background:#f0ad4e; color:white; text-decoration:none; border-radius:4px; font-size:13px;">📔 我的日记</a>' if is_owner else ''}
                </div>

                <div class="info-card">
                    <h3 style="margin-top:0;">用户信息</h3>
                    <div class="info-item"><span>用户编号</span><b>{uid}</b></div>
                    <div class="info-item"><span>用户类型</span><b>{target_role}</b></div>
                    <div class="info-item"><span>注册时间</span><b>{reg_time}</b></div>
                    <hr style="border:0; border-top:1px solid #eee; margin:15px 0;">
                    <div class="info-item"><span>基础信用</span><b>100</b></div>
                    <div class="info-item"><span>社区贡献</span><b>0</b></div>
                </div>
            </div>
        </div>
        {edit_modal}
    </body>
    </html>
    """

# ================= 6. 日记功能 (专属 URL: /rj/<uid>/<序号>) =================
@app.route('/rj')
def diary_list():
    user_id = session.get('user_id')
    if not user_id: return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, title, create_time FROM diaries WHERE user_id=? ORDER BY id DESC", (user_id,))
    diaries = c.fetchall()
    conn.close()
    
    diary_html = ""
    total = len(diaries)
    for index, d in enumerate(diaries):
        diary_index = total - index # 算出这是该用户的第几篇（从1开始，老的在最前）
        
        diary_html += f"""
        <a href="/rj/{user_id}/{diary_index}" style="display:block; text-decoration:none; color:#333; background:#fff; padding:15px 20px; border-bottom:1px solid #f0f0f0;" onmouseover="this.style.background='#f9f9f9'" onmouseout="this.style.background='#fff'">
            <div style="font-size:16px; font-weight:bold; color:#2c7be5; margin-bottom:5px;">{d[1]}</div>
            <div style="font-size:12px; color:#999;">📅 {d[2]}</div>
        </a>
        """
    if not diary_html:
        diary_html = "<p style='text-align:center; color:#999; padding:30px;'>还没有写过日记，快去记录第一篇吧！</p>"

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>我的日记</title>
        <style>
            body {{ margin:0; background:#f5f5f5; font-family:-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
            .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }}
            .main-content {{ max-width: 800px; margin: 20px auto; background:#fff; border-radius: 8px; border: 1px solid #eee; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.02); }}
            .header {{ padding:20px; border-bottom:1px solid #eee; display:flex; justify-content:space-between; align-items:center; }}
            .header h2 {{ margin:0; color:#333; font-size:18px; }}
        </style>
    </head>
    <body>
        <div class="top-nav">
            <div><a href="/" style="text-decoration:none; color:#333; font-size:18px; font-weight:bold;">← 返回首页</a></div>
            <div><a href="/logout" style="text-decoration:none; color:#666;">退出登录</a></div>
        </div>

        <div class="main-content">
            <div class="header">
                <h2>📔 我的日记</h2>
                <a href="/rj/new" style="text-decoration:none; padding:8px 15px; background:#5cb85c; color:white; border-radius:4px; font-size:14px;">写日记</a>
            </div>
            <div>{diary_html}</div>
        </div>
    </body>
    </html>
    """

@app.route('/rj/new', methods=['GET', 'POST'])
def diary_new():
    user_id = session.get('user_id')
    if not user_id: return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        if title and content:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO diaries (user_id, title, content, create_time) VALUES (?, ?, ?, ?)", (user_id, title, content, now_str))
            conn.commit()
            conn.close()
            return redirect(url_for('diary_list'))
            
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>写日记</title>
    <style>body { margin:0; background:#f5f5f5; font-family:sans-serif; } .container { max-width:600px; margin:20px auto; background:#fff; border-radius:8px; border:1px solid #eee; padding:20px; } input[type="text"] { width:100%; padding:10px; margin-bottom:15px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; font-size:16px; } textarea { width:100%; height:200px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; resize:vertical; margin-bottom:15px; font-size:14px; } button { padding:10px 20px; background:#2c7be5; color:white; border:none; border-radius:4px; cursor:pointer; font-size:15px; }</style>
    </head><body>
        <div style="text-align: right; padding: 10px 20px; background:#fff; border-bottom:1px solid #ddd;"><a href="/rj" style="color:#666; text-decoration:none; margin-right:15px;">返回列表</a><a href="/logout" style="color:#666; text-decoration:none;">退出</a></div>
        <div class="container">
            <h2 style="margin-top:0; color:#333;">✍️ 写日记</h2>
            <form method="POST">
                <input type="text" name="title" placeholder="给今天起个标题..." required>
                <textarea name="content" placeholder="今天发生了什么？..." required></textarea>
                <button type="submit">保存日记</button>
            </form>
        </div>
    </body></html>
    """

@app.route('/rj/<uid>/<int:diary_index>')
def diary_detail(uid, diary_index):
    current_user_id = session.get('user_id')
    if not current_user_id: return redirect(url_for('index'))
    
    if current_user_id != uid:
        return "无权查看他人的日记！<a href='/rj'>返回</a>"
        
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, title, content, create_time FROM diaries WHERE user_id=? ORDER BY id ASC", (uid,))
    diaries = c.fetchall()
    conn.close()
    
    if diary_index < 1 or diary_index > len(diaries):
        return "这篇日记不存在！<a href='/rj'>返回列表</a>"
        
    diary = diaries[diary_index - 1]
    
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>{diary[1]}</title>
    <style>body {{ margin:0; background:#f5f5f5; font-family:sans-serif; }} .top-nav {{ background: #fff; padding: 10px 20px; border-bottom: 1px solid #ddd; display: flex; justify-content: space-between; align-items: center; }} .container {{ max-width:600px; margin:20px auto; background:#fff; border-radius:8px; border:1px solid #eee; padding:30px; box-shadow:0 4px 12px rgba(0,0,0,0.02); }} h1 {{ color:#333; margin-top:0; border-bottom:2px solid #eee; padding-bottom:15px; }} .meta {{ color:#999; font-size:13px; margin-bottom:20px; }} .content {{ line-height:1.8; color:#333; white-space:pre-wrap; }} .btn-del {{ display:inline-block; margin-top:30px; padding:8px 15px; background:#d9534f; color:white; text-decoration:none; border-radius:4px; font-size:14px; }}</style>
    </head><body>
        <div class="top-nav">
            <div><a href="/rj" style="text-decoration:none; color:#333; font-size:18px; font-weight:bold;">← 返回日记列表</a></div>
            <div><a href="/logout" style="text-decoration:none; color:#666;">退出登录</a></div>
        </div>
        <div class="container">
            <h1>{diary[1]}</h1>
            <div class="meta">📅 {diary[3]}</div>
            <div class="content">{diary[2]}</div>
            <a href="/rj/delete/{diary[0]}" class="btn-del" onclick="return confirm('确定要撕掉这一页吗？不可恢复哦！')">删除这篇日记</a>
        </div>
    </body></html>
    """

@app.route('/rj/delete/<int:diary_id>')
def diary_delete(diary_id):
    user_id = session.get('user_id')
    if not user_id: return redirect(url_for('index'))
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("DELETE FROM diaries WHERE id=? AND user_id=?", (diary_id, user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('diary_list'))

# ================= 7. 独立反馈页面 =================
@app.route('/feedback', methods=['GET', 'POST'])
def feedback_page():
    if not session.get('username'): return redirect(url_for('index'))
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        if not content: return "<script>alert('内容不能为空！'); history.back();</script>"
        if len(content) > 100: return "<script>alert('字数不能超过 100 字！'); history.back();</script>"
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO feedbacks (user_id, content, create_time) VALUES ('0', ?, ?)", (content, now_str))
        conn.commit()
        conn.close()
        return "<script>alert('✅ 反馈已成功发送给管理员 lzm1024！'); window.location.href='/';</script>"
    return """
    <div style="max-width:500px; margin:80px auto; background:#fff; padding:30px; border-radius:8px; border:1px solid #eee; box-shadow:0 4px 12px rgba(0,0,0,0.05); font-family:sans-serif;">
        <h2 style="margin-top:0; color:#333;">✨ 意见反馈</h2>
        <p style="color:#666; font-size:14px;">有问题或建议？告诉管理员 lzm1024 吧（100字以内）</p>
        <form method="POST">
            <textarea name="content" maxlength="100" placeholder="请在此输入..." required style="width:100%; height:100px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; resize:none; margin-bottom:15px; font-family:sans-serif;"></textarea>
            <div style="display:flex; justify-content:flex-end; gap:10px;">
                <a href="/" style="text-decoration:none; padding:8px 15px; background:#ccc; color:white; border-radius:4px; font-size:14px;">取消</a>
                <button type="submit" style="padding:8px 20px; background:#2c7be5; color:white; border:none; border-radius:4px; cursor:pointer; font-size:14px;">发送反馈</button>
            </div>
        </form>
    </div>
    """

# ================= 8. 登录与注册 =================
@app.route('/dl', methods=['GET', 'POST'])
def dl():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        action = request.form.get('action')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        
        if action == 'apply_admin':
            if not password:
                conn.close()
                return jsonify({"status": "error", "message": "❌ 无密码账号不能申请管理员，请先在个人设置中设置密码！"})
            c.execute("SELECT user_id, password, last_apply_time FROM users WHERE username=?", (username,))
            user = c.fetchone()
            if not user:
                conn.close()
                return jsonify({"status": "error", "message": "账号不存在，无法申请！"})
            if not user[1]:
                conn.close()
                return jsonify({"status": "error", "message": "❌ 你的账号当前没有设置密码，请先在个人设置里设置密码后再申请！"})
            if user[1] != password:
                conn.close()
                return jsonify({"status": "error", "message": "密码错误，无法申请！"})
            user_id, db_password, last_time = user
            current_time = datetime.datetime.now().timestamp()
            if current_time - last_time < 60:
                wait_time = int(60 - (current_time - last_time))
                conn.close()
                return jsonify({"status": "error", "message": f"申请太频繁啦！<br>请等待 {wait_time} 秒后再试。"})
            c.execute("UPDATE users SET last_apply_time=?, is_applying=1 WHERE user_id=?", (current_time, user_id))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "✅ 申请已提交！<br>请等待管理员审批。"})
            
        c.execute("SELECT user_id, role FROM users WHERE username=? AND password=? AND role != '大管理员'", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['temp_user'] = username
            session['temp_role'] = user[1]
            if user[1] == '管理员':
                return jsonify({"status": "success", "redirect": "/dl/yz"})
            session['username'] = username
            session['role'] = user[1]
            session['user_id'] = user[0]
            return jsonify({"status": "success", "redirect": "/"})
        return jsonify({"status": "error", "message": "账号或密码错误！"})
        
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>登录账号</title>
    <script>
        function checkPasswordType() { var username = document.getElementById('username').value; var pwdInput = document.getElementById('password'); if (username === 'lzm1024') { pwdInput.type = 'password'; } else { pwdInput.type = 'text'; } } 
        function showModal(message) { document.getElementById('modalText').innerHTML = message; document.getElementById('modalOverlay').style.display = 'flex'; } 
        function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; } 
        async function submitForm(actionType) { 
            document.getElementById('action').value = actionType; 
            var form = document.getElementById('loginForm'); 
            var formData = new FormData(form); 
            try { 
                const response = await fetch('/dl', { method: 'POST', body: formData }); 
                const data = await response.json(); 
                if (data.status === 'success') { 
                    if (data.redirect) { window.location.href = data.redirect; } else { showModal(data.message); } 
                } else { showModal(data.message); } 
            } catch (error) { showModal("网络错误，请重试。"); } 
        } 
        window.onload = function() { 
            var urlParams = new URLSearchParams(window.location.search); 
            var u = urlParams.get('u'); 
            var p = urlParams.get('p'); 
            if (u) { 
                var usernameInput = document.getElementById('username'); 
                usernameInput.value = u; 
                checkPasswordType(); 
                if (p) { document.getElementById('password').value = p; } 
            } 
        };
    </script>
    <style>body { text-align: center; margin-top: 100px; font-family: sans-serif; }.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); justify-content: center; align-items: center; z-index: 1000; }.modal-box { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-align: center; width: 320px; font-family: sans-serif; }.modal-box h3 { margin-top: 0; color: #333; }.modal-box p { color: #666; margin-bottom: 25px; line-height: 1.5; }.modal-box button { width: 100%; padding: 10px 0; background-color: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }.modal-box button:hover { background-color: #0056b3; }input[type="text"], input[type="password"] { padding: 8px; width: 250px; }button[type="button"] { padding: 8px 15px; cursor: pointer; }</style></head>
    <body>
        <h2>登录账号</h2>
        <form id="loginForm" onsubmit="event.preventDefault();">
            <input type="text" id="username" name="username" placeholder="用户名" oninput="checkPasswordType()" required><br><br>
            <input type="text" id="password" name="password" placeholder="密码" required><br><br>
            <label><input type="checkbox" checked> 保持登录</label><br><br>
            <button type="button" onclick="submitForm('login')">下一步</button>
            <button type="button" onclick="submitForm('apply_admin')">申请成为管理员</button>
            <input type="hidden" name="action" id="action" value="login">
        </form>
        <br><a href="/zc">创建账号</a>
        <div id="modalOverlay" class="modal-overlay"><div class="modal-box"><h3>提示</h3><p id="modalText"></p><button onclick="closeModal()">返回</button></div></div>
    </body></html>
    """

@app.route('/dgldl', methods=['GET', 'POST'])
def dgldl():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT user_id, role FROM users WHERE username=? AND password=? AND role='大管理员'", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['username'] = username
            session['role'] = '大管理员'
            session['user_id'] = user[0]
            return jsonify({"status": "success", "redirect": "/"})
        return jsonify({"status": "error", "message": "❌ 账号或密码错误！"})
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>核心系统入口</title>
    <script>
        function showModal(message) { document.getElementById('modalText').innerHTML = message; document.getElementById('modalOverlay').style.display = 'flex'; } 
        function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; } 
        async function submitAdminLogin() { 
            var form = document.getElementById('adminForm'); 
            var formData = new FormData(form); 
            try { 
                const response = await fetch('/dgldl', { method: 'POST', body: formData }); 
                const data = await response.json(); 
                if (data.status === 'success') { window.location.href = data.redirect; } else { showModal(data.message); } 
            } catch (error) { showModal("网络错误，请重试。"); } 
        }
    </script>
    <style>body { text-align: center; margin-top: 100px; font-family: sans-serif; background-color: #f5f6f7; }.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); justify-content: center; align-items: center; z-index: 1000; }.modal-box { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-align: center; width: 320px; font-family: sans-serif; }.modal-box h3 { margin-top: 0; color: #333; }.modal-box p { color: #666; margin-bottom: 25px; line-height: 1.5; }.modal-box button { width: 100%; padding: 10px 0; background-color: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }input[type="text"] { padding: 10px; width: 250px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px; }</style></head>
    <body>
        <h2>🔒 核心系统入口</h2>
        <form id="adminForm" onsubmit="event.preventDefault();">
            <input type="text" name="username" placeholder="核心用户名" required><br>
            <input type="text" name="password" placeholder="密码" required><br>
            <label><input type="checkbox" checked> 保持登录</label><br><br>
            <button type="button" onclick="submitAdminLogin()" style="padding:10px 30px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">验证登录</button>
        </form>
        <div id="modalOverlay" class="modal-overlay"><div class="modal-box"><h3>提示</h3><p id="modalText"></p><button onclick="closeModal()">返回</button></div></div>
    </body></html>
    """

@app.route('/zc', methods=['GET', 'POST'])
def zc():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password', '').strip()
        password2 = request.form.get('password2', '').strip()
        if not re.match(r'^[a-zA-Z]', username) or not (4 <= len(username) <= 10) or not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({"status": "error", "message": "账号格式不符合要求！"})
        if password:
            if not (6 <= len(password) <= 12):
                return jsonify({"status": "error", "message": "密码长度必须在 6 到 12 位之间！"})
        if password != password2:
            return jsonify({"status": "error", "message": "两次输入的密码不一致！"})
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (username,))
        if c.fetchone():
            conn.close()
            return jsonify({"status": "error", "message": "该账号已被注册！"})
        c.execute("SELECT user_id FROM users WHERE role='普通用户'")
        normal_users = c.fetchall()
        max_id = 0
        for u in normal_users:
            try:
                num = int(u[0])
                if num > max_id: max_id = num
            except: pass
        new_id = str(max_id + 1).zfill(4) 
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute("INSERT INTO users (user_id, username, password, role, register_time) VALUES (?, ?, ?, '普通用户', ?)", (new_id, username, password, now_time))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": f"✅ 注册成功！<br>你的专属用户ID是：<b>{new_id}</b>", "username": username, "password": password})
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>注册账号</title>
    <style>body { text-align: center; margin: 0; padding-top: 80px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #ffffff; }.form-box { background: #ffffff; width: 350px; margin: 0 auto; padding: 30px 40px; border: 1px solid #e0e0e0; }.logo-title { font-size: 22px; font-weight: bold; color: #333; margin-bottom: 25px; }.input-group { position: relative; margin-bottom: 5px; }.input-group svg.input-icon { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); width: 16px; height: 16px; fill: #999; }input[type="text"], input[type="password"] { padding: 12px 12px 12px 35px; width: 100%; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; font-size: 14px; background-color: #fff; transition: border-color 0.3s; }input[type="text"]:focus, input[type="password"]:focus { border-color: #5cb85c; outline: none; }.rules-box { text-align: left; font-size: 12px; margin-top: 5px; margin-bottom: 15px; padding-left: 2px; color: #888; }.rule-item { display: flex; align-items: center; margin-bottom: 2px; transition: color 0.3s; line-height: 1.2; }.icon-wrap { display: inline-flex; justify-content: center; align-items: center; width: 14px; height: 14px; margin-right: 6px; font-weight: bold; }.svg-icon { width: 14px; height: 14px; display: none; }.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); justify-content: center; align-items: center; z-index: 1000; }.modal-box { background: white; padding: 25px; border: 1px solid #ccc; text-align: center; width: 300px; }.modal-box h3 { margin-top: 0; color: #333; font-size: 18px; }.modal-box p { color: #666; margin-bottom: 20px; line-height: 1.5; font-size: 14px; }.modal-box button { width: 100%; padding: 10px 0; border: none; font-size: 15px; color: white; border-radius: 4px; }.bottom-link { display: block; margin-top: 15px; text-decoration: none; color: #007bff; font-size: 13px; }.bottom-link:hover { text-decoration: underline; }</style>
    <script>
        var tempU = '', tempP = '';
        var iconGray = '<span style="color:#ccc;">·</span>';
        var iconGreen = '<svg class="svg-icon" style="display:inline-block;" viewBox="0 0 24 24" fill="#5cb85c"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>';
        var iconRed = '<svg class="svg-icon" style="display:inline-block;" viewBox="0 0 24 24" fill="#d9534f"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>';
        function updateRule(elementId, condition, isNotEmpty) { var el = document.getElementById(elementId); var iconSpan = el.querySelector('.icon-wrap'); if (!isNotEmpty) { iconSpan.innerHTML = iconGray; el.style.color = '#888'; } else { if (condition) { iconSpan.innerHTML = iconGreen; el.style.color = '#333'; } else { iconSpan.innerHTML = iconRed; el.style.color = '#d9534f'; } } }
        function checkUsername() { var val = document.getElementById('regUser').value; var isNotEmpty = val.length > 0; updateRule('ruleLen', val.length >= 4 && val.length <= 10, isNotEmpty); updateRule('ruleStart', /^[a-zA-Z]/.test(val), isNotEmpty); updateRule('ruleChar', /^[a-zA-Z0-9_]+$/.test(val), isNotEmpty); }
        function checkPassword() { var val = document.getElementById('regPwd').value; var isNotEmpty = val.length > 0; updateRule('rulePwdLen', val.length >= 6 && val.length <= 12, isNotEmpty); }
        function showModal(message, isSuccess, username, password) { var modalText = document.getElementById('modalText'); var modalBtn = document.getElementById('modalBtn'); modalText.innerHTML = message; document.getElementById('modalOverlay').style.display = 'flex'; if (isSuccess) { tempU = username; tempP = password; modalBtn.disabled = true; modalBtn.style.backgroundColor = '#cccccc'; modalBtn.style.cursor = 'not-allowed'; modalBtn.innerText = '我知道了 (2s)'; var timeLeft = 2; var timer = setInterval(function() { timeLeft--; if (timeLeft > 0) { modalBtn.innerText = '我知道了 (' + timeLeft + 's)'; } else { clearInterval(timer); modalBtn.disabled = false; modalBtn.style.backgroundColor = '#007bff'; modalBtn.style.cursor = 'pointer'; modalBtn.innerText = '我知道了'; } }, 1000); } else { tempU = ''; tempP = ''; modalBtn.disabled = false; modalBtn.style.backgroundColor = '#007bff'; modalBtn.style.cursor = 'pointer'; modalBtn.innerText = '返回修改'; } }
        function closeModal() { document.getElementById('modalOverlay').style.display = 'none'; }
        function handleModalBtn() { closeModal(); if (tempU !== '') { window.location.href = '/dl?u=' + encodeURIComponent(tempU) + '&p=' + encodeURIComponent(tempP); } }
        async function submitRegister() { var form = document.getElementById('regForm'); var formData = new FormData(form); try { const response = await fetch('/zc', { method: 'POST', body: formData }); const data = await response.json(); if (data.status === 'success') { showModal(data.message, true, data.username, data.password); } else { showModal(data.message, false); } } catch (error) { showModal("网络错误，请重试。", false); } }
    </script>
    </head>
    <body>
        <div class="form-box">
            <div class="logo-title">注册账号</div>
            <form id="regForm" onsubmit="event.preventDefault();">
                <div class="input-group"><input type="text" id="regUser" name="username" placeholder="设置账号" oninput="checkUsername()" required><svg class="input-icon" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg></div>
                <div class="rules-box"><div id="ruleLen" class="rule-item"><span class="icon-wrap"><span style="color:#ccc;">·</span></span>长度为 4~10 位</div><div id="ruleStart" class="rule-item"><span class="icon-wrap"><span style="color:#ccc;">·</span></span>开头为字母</div><div id="ruleChar" class="rule-item"><span class="icon-wrap"><span style="color:#ccc;">·</span></span>只包含字母、数字和下划线</div></div>
                <div class="input-group"><input type="password" id="regPwd" name="password" placeholder="设置密码" oninput="checkPassword()"><svg class="input-icon" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg></div>
                <div class="rules-box"><div id="rulePwdLen" class="rule-item"><span class="icon-wrap"><span style="color:#ccc;">·</span></span>密码需为 6~12 位（留空则无密码）</div></div>
                <div class="input-group"><input type="password" name="password2" placeholder="再次确认密码"><svg class="input-icon" viewBox="0 0 24 24"><path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/></svg></div>
                <button type="button" onclick="submitRegister()" style="margin-top: 20px; padding:12px 30px; background-color: #5cb85c; color:white; border:none; border-radius: 4px; cursor:pointer; width:100%; font-size:15px;">注册</button>
            </form>
            <a href="/dl" class="bottom-link">已有账号？去登录</a>
        </div>
        <div id="modalOverlay" class="modal-overlay"><div class="modal-box"><h3>提示</h3><p id="modalText"></p><button id="modalBtn" onclick="handleModalBtn()">我知道了</button></div></div>
    </body></html>
    """

@app.route('/dl/yz', methods=['GET', 'POST'])
def yz():
    if 'temp_user' not in session or session.get('temp_role') != '管理员':
        return redirect(url_for('dl'))
    current_hour = datetime.datetime.now().hour
    binary_hour = bin(current_hour)[2:] 
    if request.method == 'POST':
        input_code = request.form.get('code')
        zero_count = binary_hour.count('0') 
        correct_code = f"{current_hour}{zero_count}"
        if input_code == correct_code:
            session['username'] = session.pop('temp_user')
            session['role'] = session.pop('temp_role')
            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("SELECT user_id FROM users WHERE username=? AND role='管理员'", (session['username'],))
            res = c.fetchone()
            if res: session['user_id'] = res[0]
            conn.close()
            return jsonify({"status": "success", "redirect": "/"})
        else:
            return jsonify({"status": "error", "message": "动态密码错误！请重新输入。"})
    return f"""
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>二次验证</title>
    <script>function showModal(message) {{ document.getElementById('modalText').innerHTML = message; document.getElementById('modalOverlay').style.display = 'flex'; }}function closeModal() {{ document.getElementById('modalOverlay').style.display = 'none'; }}async function submitVerify() {{ var form = document.getElementById('yzForm'); var formData = new FormData(form); try {{ const response = await fetch('/dl/yz', {{ method: 'POST', body: formData }}); const data = await response.json(); if (data.status === 'success') {{ window.location.href = data.redirect; }} else {{ showModal(data.message); }} }} catch (error) {{ showModal("网络错误，请重试。"); }} }}</script>
    <style>body {{ text-align: center; margin-top: 100px; font-family: sans-serif; background-color: #f5f6f7; }}.modal-overlay {{ display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.4); justify-content: center; align-items: center; z-index: 1000; }}.modal-box {{ background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); text-align: center; width: 320px; font-family: sans-serif; }}.modal-box h3 {{ margin-top: 0; color: #333; }}.modal-box p {{ color: #666; margin-bottom: 25px; line-height: 1.5; }}.modal-box button {{ width: 100%; padding: 10px 0; background-color: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; }}input[type="text"] {{ padding: 10px; width: 250px; border: 1px solid #ccc; border-radius: 4px; margin-bottom: 15px; box-sizing: border-box; }}</style></head>
    <body><h2>🔒 二次验证</h2><form id="yzForm" onsubmit="event.preventDefault();"><input type="text" name="code" placeholder="{binary_hour}" required><br><button type="button" onclick="submitVerify()" style="padding:10px 30px; background:#007bff; color:white; border:none; border-radius:4px; cursor:pointer;">验证</button></form><div id="modalOverlay" class="modal-overlay"><div class="modal-box"><h3>提示</h3><p id="modalText"></p><button onclick="closeModal()">返回</button></div></div></body></html>
    """

# ================= 9. 大管理控制台 =================
@app.route('/admin', methods=['GET', 'POST'])
def admin_console():
    if session.get('role') != '大管理员': return "无权访问！<a href='/'>返回首页</a>", 403
    
    if not session.get('key_verified'):
        if request.method == 'POST' and 'key_file' in request.files:
            key_file = request.files.get('key_file')
            if not key_file: return "<script>alert('请选择密钥文件！'); history.back();</script>"
            uploaded_content = key_file.read().decode('utf-8').strip()
            if uploaded_content != "LZM1024_SUPER_SECRET_KEY_2026_DO_NOT_SHARE": return "<script>alert('❌ 密钥内容错误！'); history.back();</script>"
            session['key_verified'] = True
            return redirect(url_for('admin_console'))
            
        return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>安全验证</title><style>body { text-align: center; margin-top: 100px; font-family: sans-serif; background-color: #f5f6f7; }.box { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: inline-block; }input[type="file"] { margin: 20px 0; }button { padding: 10px 30px; background: #d9534f; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }</style></head><body><div class="box"><h2>🛡️ 高危操作安全验证</h2><p style="color:#666;">每次进入控制台均需验证物理密钥</p><form method="POST" enctype="multipart/form-data"><input type="file" name="key_file" accept=".key,.txt" required><br><button type="submit">验证密钥并进入</button></form><br><br><a href="/user/0" style="color:#666; text-decoration:none; font-size:14px;">放弃并返回</a></div></body></html>"""

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    if request.method == 'POST' and 'publish_ann' in request.form:
        ann_content = request.form.get('ann_content')
        if ann_content:
            now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute("INSERT INTO announcements (content, publish_time) VALUES (?, ?)", (ann_content, now_str))
            conn.commit()
            return redirect(url_for('admin_console'))

    if request.method == 'POST' and 'appoint_uid' in request.form:
        target_uid = request.form.get('appoint_uid')
        c.execute("SELECT COUNT(*) FROM users WHERE role='管理员'")
        current_admin_count = c.fetchone()[0]
        if current_admin_count >= 20:
            conn.close()
            return "<script>alert('管理员名额已满（20人），无法任命！'); window.location.href='/admin';</script>"
        
        c.execute("UPDATE users SET role='管理员', is_applying=0 WHERE user_id=?", (target_uid,))
        conn.commit()
        conn.close()
        return "<script>alert('任命成功！该用户已晋升为管理员。'); window.location.href='/admin';</script>"

    c.execute("SELECT COUNT(*) FROM users WHERE role='管理员'")
    current_admin_count = c.fetchone()[0]
    c.execute("SELECT DISTINCT user_id, username, nickname FROM users WHERE is_applying=1 ORDER BY user_id ASC")
    applicants = c.fetchall()
    c.execute("SELECT id, user_id, content, create_time FROM feedbacks ORDER BY id DESC")
    feedbacks = c.fetchall()
    c.execute("SELECT user_id, nickname, username FROM users WHERE role='普通用户' LIMIT 20")
    normal_users = c.fetchall()
    conn.close()
    
    app_html = ""
    for app in applicants:
        uid, uname, nickname = app
        nick = nickname if nickname else uname
        app_html += f"""<div style="display:flex; justify-content:space-between; align-items:center; background:#f9f9f9; padding:15px; margin-bottom:10px; border-radius:6px; border:1px solid #eee;"><div><b style="color:#333;">{nick}</b> <span style="color:#888; font-size:13px;">(ID: {uid} / 账号: {uname})</span></div><form method="POST" action="/approve_admin/{uid}" style="margin:0;"><button type="submit" style="padding:6px 15px; background:#5cb85c; color:white; border:none; border-radius:4px; cursor:pointer;">同意申请</button></form></div>"""
    if not app_html: app_html = "<p style='color:#888;'>当前没有待审批的申请。</p>"
    quota_warning = ""
    if current_admin_count >= 20:
        quota_warning = "<p style='color:red; font-weight:bold;'>⚠️ 管理员名额已满（20/20），无法继续批准。</p>"
        app_html = "<p style='color:#888;'>名额已满，暂不处理。</p>"
    fb_html = ""
    for fb in feedbacks:
        f_id, f_uid, f_content, f_time = fb
        fb_html += f"""<details style="background:#f9f9f9; border:1px solid #eee; border-radius:6px; padding:10px; margin-bottom:10px;"><summary style="cursor:pointer; color:#333; font-size:14px; font-weight:bold;">【{f_time}】用户 {f_uid} 的反馈 <span style="color:#888; font-weight:normal; font-size:12px;">(点击查看)</span></summary><div style="margin-top:10px; padding-top:10px; border-top:1px dashed #ccc; color:#555; font-size:14px; word-break: break-all;">{f_content}</div></details>"""
    if not fb_html: fb_html = "<p style='color:#888;'>暂无反馈。</p>"
    
    appoint_options = "".join([f"<option value='{u[0]}'>{u[1] if u[1] else u[2]} (ID: {u[0]})</option>" for u in normal_users])
    if not appoint_options:
        appoint_options = "<option value=''>当前没有可任命的普通用户</option>"
        
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>管理控制台</title><style>body {{ background-color: #f5f6f7; font-family: sans-serif; padding: 40px; margin: 0; }}.box {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}h2 {{ margin-top: 0; color: #333; border-bottom: 2px solid #d9534f; padding-bottom: 10px; display: inline-block; }}</style></head><body><div class="box"><h2>👑 管理控制台</h2><div style="margin-bottom: 20px; font-size: 15px;">当前管理员人数：<b style="color:{'red' if current_admin_count >= 20 else 'green'};">{current_admin_count} / 20</b><a href="/logout" style="float:right; color:#d9534f; text-decoration:none; font-size:14px;">退出登录</a></div>{quota_warning}<h3>📝 管理员申请列表</h3>{app_html}<hr style="border:0; border-top:1px solid #eee; margin:30px 0;"><h3>👑 直接任命新管理员</h3><form method="POST" style="display:flex; gap:10px; align-items:center; margin-top: 15px;"><select name="appoint_uid" required style="padding:10px; border-radius:4px; border:1px solid #ccc; flex:1;">{appoint_options}</select><button type="submit" style="padding:10px 20px; background:#d9534f; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">直接任命</button></form><hr style="border:0; border-top:1px solid #eee; margin:30px 0;"><h3>📢 发布站内公告</h3><form method="POST" style="margin-top:15px;"><input type="hidden" name="publish_ann" value="1"><textarea name="ann_content" placeholder="输入公告内容..." required style="width:100%; height:80px; padding:10px; border:1px solid #ccc; border-radius:4px; box-sizing:border-box; resize:vertical; margin-bottom:10px;"></textarea><button type="submit" style="padding:8px 20px; background:#f0ad4e; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">发布公告</button></form><hr style="border:0; border-top:1px solid #eee; margin:30px 0;"><h3>📬 用户反馈收件箱 (管理员 lzm1024 收)</h3><div style="margin-top: 15px;">{fb_html}</div><br><br><a href="/user/0" style="color:#666; text-decoration:none;">← 返回个人中心</a></div></body></html>"""

@app.route('/approve_admin/<uid>', methods=['POST'])
def approve_admin(uid):
    if session.get('role') != '大管理员': return "无权操作", 403
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users WHERE role='管理员'")
    if c.fetchone()[0] >= 20:
        conn.close()
        return "<script>alert('管理员名额已满！'); window.location.href='/admin';</script>"
    c.execute("UPDATE users SET role='管理员', is_applying=0 WHERE user_id=?", (uid,))
    conn.commit()
    conn.close()
    return "<script>alert('审批通过！该用户已成为管理员。'); window.location.href='/admin';</script>"

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)