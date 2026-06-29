"""球场广告 API"""
from flask import Blueprint, request

from wxcloudrun.models import AdZone, AdCampaign
from wxcloudrun.response import success_response

bp = Blueprint("stadium", __name__, url_prefix="/api/v1/stadium")


@bp.get("/zones")
def list_zones():
    zones = AdZone.query.order_by(AdZone.id).all()
    items = [
        {
            "id": z.id,
            "position": z.position,
            "size_category": z.size_category,
            "width": z.width,
            "height": z.height,
            "label": z.label,
        }
        for z in zones
    ]
    return success_response({"zones": items})


@bp.get("/ads")
def list_ads():
    match_id = request.args.get("match_id", type=int)
    campaigns = AdCampaign.query.filter_by(is_active=True).all()
    ads = [
        {
            "zone_id": c.zone_id,
            "advertiser_name": c.advertiser_name,
            "slogan": c.slogan,
            "bg_color": c.bg_color,
            "text_color": c.text_color,
            "logo_text": c.logo_text,
        }
        for c in campaigns
    ]
    return success_response({"zones": [], "ads": ads, "match_id": match_id})
