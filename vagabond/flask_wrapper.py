from vagabond.analytics.module import update_fingerprint_impressions
from vagabond.constants import SuccessMessage, RouteError
from flask import Response, jsonify, render_template
import logging

from vagabond.services import dbmanager as db
log = logging.getLogger(__name__)

def success_response(status: SuccessMessage, http_code: int = 200) -> tuple[Response, int]:
    payload = {
        "success": status.value
    }

    return jsonify(payload), http_code

def error_response(status: RouteError, http_code: int = 400, extra_info: dict = None) -> tuple[Response, int]:
    payload = {
        "error": status.value
    }

    if extra_info:
        payload.update(extra_info)

    return jsonify(payload), http_code

def custom_render_template(template_name: str, **context):

    update_fingerprint_impressions(page_name=template_name)
    
    return render_template(template_name, **context)