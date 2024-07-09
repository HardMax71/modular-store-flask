import json
from typing import Dict, Optional

from modules.db.database import db
from modules.db.models import Wishlist


def get_variant_options(variant_options_json: Optional[str]) -> Dict[str, str]:
    """
    Parse JSON-encoded variant options into a dictionary.

    Args:
        variant_options_json (Optional[str]): JSON-encoded string of variant options.

    Returns:
        Dict[str, str]: A dictionary of variant options, or an empty dict if input is None or invalid.
    """
    if variant_options_json:
        try:
            return json.loads(variant_options_json)
        except json.JSONDecodeError:
            return {}
    return {}


def wishlist_exists(user_id: int, goods_id: int) -> Optional[Wishlist]:
    """
    Check if a wishlist item exists for the given user and goods.

    Args:
        user_id (int): The ID of the user.
        goods_id (int): The ID of the goods.

    Returns:
        Optional[Wishlist]: The wishlist item if it exists, otherwise None.
    """
    return db.session.query(Wishlist).filter_by(user_id=user_id, goods_id=goods_id).first()


def remove_from_wishlist(user_id: int, goods_id: int) -> None:
    """
    Remove an item from the user's wishlist.

    Args:
        user_id (int): The ID of the user.
        goods_id (int): The ID of the goods to remove.

    Returns:
        None
    """
    wishlist_item = db.session.query(Wishlist).filter_by(user_id=user_id, goods_id=goods_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        db.session.commit()


def add_wishlist_item(user_id: int, goods_id: int, variant_options: Dict[str, str]) -> None:
    """
    Add an item to the user's wishlist.

    Args:
        user_id (int): The ID of the user.
        goods_id (int): The ID of the goods to add.
        variant_options (Dict[str, str]): The variant options for the goods.

    Returns:
        None
    """
    variant_options_str = json.dumps(variant_options)
    new_wishlist_item = Wishlist(user_id=user_id, goods_id=goods_id, variant_options=variant_options_str)
    db.session.add(new_wishlist_item)
    db.session.commit()
