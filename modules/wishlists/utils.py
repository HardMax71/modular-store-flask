import json

from modules.db.database import db
from modules.db.models import Wishlist


def get_variant_options(variant_options_json):
    if variant_options_json:
        return json.loads(variant_options_json)
    return {}


def is_wishlist_item_exists(user_id, goods_id, variant_options):
    return Wishlist.query.filter_by(user_id=user_id, goods_id=goods_id).first()


def remove_from_wishlist(user_id, goods_id, variant_options):
    wishlist_item = Wishlist.query.filter_by(user_id=user_id, goods_id=goods_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()


def add_wishlist_item(user_id, goods_id, variant_options):
    variant_options_str = json.dumps(variant_options)
    new_wishlist_item = Wishlist(user_id=user_id, goods_id=goods_id, variant_options=variant_options_str)
    db.session.add(new_wishlist_item)
    db.session.commit()
