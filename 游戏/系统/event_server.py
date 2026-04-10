
from flask import Flask, request, send_from_directory, jsonify
import os
import json


app = Flask(__name__)
CONFIG_FILE = 'event_config.json'
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

# 默认配置（可根据实际需要调整）
default_config = {
    "events": [
        {
            "name": "事件A", "t50": 10, "wTime": 1, "wUrge": 1, "interval": 30, "lastGrantedTime": 0, "lastAskedTime": 0, "rewardMultiplier": 1, "askCost": 0, "ruleText": '',
            "urgeLabels": {"1": "几乎不想", "2": "似乎有点想", "3": "如果顺便的话想做", "4": "明确想要做了", "5": "非常想要做", "6": "不做有点难以忍受", "7": "需要全力忍受", "8": "完全忍不住了"}
        },
        {
            "name": "事件B", "t50": 100, "wTime": 2, "wUrge": 1, "interval": 60, "lastGrantedTime": 0, "lastAskedTime": 0, "rewardMultiplier": 1, "askCost": 0, "ruleText": '',
            "urgeLabels": {"1": "几乎不想", "2": "似乎有点想", "3": "如果顺便的话想做", "4": "明确想要做了", "5": "非常想要做", "6": "不做有点难以忍受", "7": "需要全力忍受", "8": "完全忍不住了"}
        }
    ],
    "rewardStock": 0,
    "tasks": []
}
@app.route('/config', methods=['GET', 'POST'])
def config():
    if request.method == 'GET':
        if not os.path.exists(CONFIG_FILE):
            # 自动创建默认配置
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            return jsonify(default_config)
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    elif request.method == 'POST':
        data = request.get_json(force=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({"ok": True})

@app.route('/')
def index():
    return send_from_directory(WEB_DIR, '概率决定.html')


# 兼容原有接口
@app.route('/event_config.json', methods=['GET'])
def get_config_compat():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return f.read(), 200, {'Content-Type': 'application/json'}
    return '{}', 200, {'Content-Type': 'application/json'}

@app.route('/event_config.json', methods=['POST'])
def save_config_compat():
    data = request.get_data(as_text=True)
    try:
        json.loads(data)  # 校验 JSON
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(data)
        return 'OK', 200
    except Exception as e:
        return 'Invalid JSON', 400

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(WEB_DIR, path)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
