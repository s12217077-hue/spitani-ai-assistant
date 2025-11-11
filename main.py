from flask import Flask, request, jsonify
import os, requests, xmlrpc.client

app = Flask(__name__)

ODOO_URL = os.environ.get("ODOO_URL")
ODOO_DB = os.environ.get("ODOO_DB")
ODOO_LOGIN = os.environ.get("ODOO_LOGIN_EMAIL")
ODOO_API_KEY = os.environ.get("ODOO_API_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

COMMON = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/common")
OBJECTS = xmlrpc.client.ServerProxy(f"{ODOO_URL}/xmlrpc/2/object")

def odoo_uid():
    return COMMON.authenticate(ODOO_DB, ODOO_LOGIN, ODOO_API_KEY, {})

def search_products(uid, query, limit=5):
    domain = ["|", ("name", "ilike", query), ("description_sale", "ilike", query)]
    fields = ["name", "list_price", "currency_id", "website_url"]
    ids = OBJECTS.execute_kw(ODOO_DB, uid, ODOO_API_KEY,
                             "product.template", "search",
                             [domain], {"limit": limit})
    if not ids:
        return []
    return OBJECTS.execute_kw(ODOO_DB, uid, ODOO_API_KEY,
                              "product.template", "read", [ids], {"fields": fields})

def call_ai(user_query, products):
    model = "gpt-4o-mini"
    system = "You are Spitani AI Assistant. Reply in the same language as user (Arabic or English). Use data from product list when possible."
    prompt = f"User asked: {user_query}\nProducts: {products}"

    res = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": model, "messages":[{"role":"system","content":system},{"role":"user","content":prompt}]}
    )
    return res.json()["choices"][0]["message"]["content"]

@app.post("/assist")
def assist():
    data = request.get_json(force=True)
    q = data.get("message","").strip()
    if not q:
        return jsonify({"ok": False, "error": "empty message"})
    uid = odoo_uid()
    products = search_products(uid, q)
    answer = call_ai(q, products)
    return jsonify({"ok": True, "answer": answer})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
