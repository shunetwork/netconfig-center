#!/usr/bin/env python3
"""
NetManagerX测试服务器
最简单的Flask应用测试
"""

from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <html>
    <head><title>NetManagerX</title></head>
    <body>
        <h1>NetManagerX 网络配置管理系统</h1>
        <p>服务已启动！</p>
        <p>访问地址: http://localhost:5000</p>
        <p>健康检查: <a href="/health">/health</a></p>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return jsonify({'status': 'OK', 'message': 'NetManagerX is running'})

if __name__ == '__main__':
    print("NetManagerX测试服务器启动中...")
    print("访问地址: http://localhost:5000")
    print("按 Ctrl+C 停止服务器")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
