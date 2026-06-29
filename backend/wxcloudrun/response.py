"""统一 JSON 响应（兼容小程序现有格式）"""
import json
from flask import Response


def success_response(data=None, message="success", status_code=200):
    body = json.dumps({"code": 0, "message": message, "data": data}, ensure_ascii=False)
    return Response(body, status=status_code, mimetype="application/json")


def error_response(message="error", status_code=400, code=1):
    body = json.dumps({"code": code, "message": message, "data": None}, ensure_ascii=False)
    return Response(body, status=status_code, mimetype="application/json")
