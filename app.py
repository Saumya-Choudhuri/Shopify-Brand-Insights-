import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from schemas import BrandContextRequest, BrandContext
from shopify_insights import get_brand_context, is_shopify_site
from db import save_snapshot, latest_snapshots
from competitors import competitor_contexts

app = Flask(__name__, static_folder="static")
CORS(app)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("brand-insights")

# -------- Serve the UI at root --------
@app.route("/", methods=["GET"])
def serve_index():
    # Opens your frontend without typing /static/index.html
    return send_from_directory(app.static_folder, "index.html")

# Optional: keep a JSON health endpoint
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"message": "Shopify Brand Insights API is live", "health": "ok"}), 200

# Keep serving any other static assets (css/js/images) if you add them
@app.route("/static/<path:path>", methods=["GET"])
def static_files(path):
    return send_from_directory(app.static_folder, path)

# -------- API endpoints --------
@app.route("/api/brand-context", methods=["POST"])
def brand_context():
    try:
        data = request.get_json(silent=True) or {}
        req = BrandContextRequest(**data)
        ok, reason = is_shopify_site(req.website_url)
        if not ok:
            return jsonify({"error": f"website not reachable or not Shopify-like: {reason}"}), 401

        context = get_brand_context(req.website_url)
        # validate against schema for clean output
        ctx = BrandContext(**context).model_dump(mode="json")
        return jsonify(ctx), 200
    except Exception as e:
        log.exception("brand_context failed")
        return jsonify({"error": "internal server error", "details": str(e)}), 500

@app.route("/api/brand-context/save", methods=["POST"])
def brand_context_and_save():
    try:
        data = request.get_json(silent=True) or {}
        req = BrandContextRequest(**data)
        ok, reason = is_shopify_site(req.website_url)
        if not ok:
            return jsonify({"error": f"website not reachable or not Shopify-like: {reason}"}), 401

        context = get_brand_context(req.website_url)
        ctx = BrandContext(**context).model_dump(mode="json")
        snapshot_id = save_snapshot(ctx["store"]["url"], ctx)
        return jsonify({"snapshot_id": snapshot_id, "store": ctx["store"], "saved": True}), 200
    except Exception as e:
        log.exception("save failed")
        return jsonify({"error": "internal server error", "details": str(e)}), 500

@app.route("/api/snapshots", methods=["GET"])
def list_snapshots():
    try:
        return jsonify({"latest": latest_snapshots(10)}), 200
    except Exception as e:
        return jsonify({"error": "internal server error", "details": str(e)}), 500

@app.route("/api/competitors", methods=["POST"])
def get_competitors():
    """
    Body:
      {
        "website_url": "https://brand.com",
        "loose": false,   # optional; if true, returns best-effort candidates
        "limit": 3        # optional; default 3
      }
    """
    try:
        data = request.get_json(silent=True) or {}
        website_url = data.get("website_url")
        loose = bool(data.get("loose", False))
        limit = int(data.get("limit", 3))

        if not website_url:
            return jsonify({"error": "website_url is required"}), 400

        results = competitor_contexts(website_url, limit=limit, loose=loose)
        return jsonify({"seed": website_url, "competitors": results}), 200
    except Exception as e:
        log.exception("competitors failed")
        return jsonify({"error": "internal server error", "details": str(e)}), 500

if __name__ == "__main__":
    # TIP: run with COMP_DEBUG=1 to see competitor debug logs
    # export COMP_DEBUG=1 && python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)