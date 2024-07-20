import json
from typing import Dict, Optional

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Wishlist


def get_product_selection_options(selection_options_json: Optional[str]) -> Dict[str, str]:
    """
    Parse JSON-encoded variant options into a dictionary.

    Args:
        selection_options_json (Optional[str]): JSON-encoded string of variant options.

    Returns:
        Dict[str, str]: A dictionary of variant options, or an empty dict if input is None or invalid.
    """
    if selection_options_json:
        try:
            return json.loads(selection_options_json)  # type: ignore
        except json.JSONDecodeError:
            return {}
    return {}


def wishlist_exists(user_id: int, product_id: int) -> Optional[Wishlist]:
    return db.session.query(Wishlist).filter_by(user_id=user_id, product_id=product_id).first()


def remove_from_wishlist(user_id: int, product_id: int) -> None:
    wishlist_item = db.session.query(Wishlist).filter_by(user_id=user_id, product_id=product_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()


def add_wishlist_item(user_id: int, product_id: int, variant_options: Dict[str, str]) -> None:
    variant_options_str = json.dumps(variant_options)
    new_wishlist_item = Wishlist(user_id=user_id, product_id=product_id, variant_options=variant_options_str)
    db.session.add(new_wishlist_item)
    db.session.commit()
