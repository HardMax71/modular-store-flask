import json
from math import ceil
from typing import Optional, List, Dict

from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask import send_from_directory, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user
from sqlalchemy import exists, desc
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload

from config import AppConfig
from modules.carts import apply_discount_code
from modules.db.database import db
from modules.db.models import Goods, Variant, Review, User, Wishlist, RecentlyViewedProduct, \
    ComparisonHistory
from modules.decorators import login_required_with_message
from modules.filter import get_filter_options, filter_products, paginate_query, get_promoted_products, get_categories
from modules.recommendations import get_recommended_products, update_recently_viewed_products
from modules.reviews import has_purchased

main_bp = Blueprint('main', __name__)


@main_bp.route("/")
def index() -> ResponseValue:
    if 'filter_options' not in session:
        session['filter_options'] = get_filter_options()

    page: int = request.args.get('page', 1, type=int)
    shirts_query = filter_products(None, None, None).options(joinedload(Goods.tags))
    paginated_query, in_total, total_pages, per_page = paginate_query(shirts_query, page)

    return render_template("index.html", shirts=paginated_query, current_page=page, total_pages=total_pages,
                           categories=get_categories(), promoted_products=get_promoted_products(), per_page=per_page,
                           in_total=in_total)


@main_bp.route("/search")
def search_route() -> ResponseValue:
    query: Optional[str] = request.args.get('query')
    page: int = request.args.get('page', 1, type=int)
    per_page: int = AppConfig.PER_PAGE

    search_query = filter_products(name_query=query)
    total: int = search_query.count()
    offset: int = (page - 1) * per_page
    paginated_shirts: List[Goods] = search_query.offset(offset).limit(per_page).all()
    total_pages: int = ceil(total / per_page)

    return render_template("index.html", shirts=paginated_shirts, query=query, total_pages=total_pages,
                           current_page=page, per_page=per_page, in_total=total, categories=get_categories(),
                           promoted_products=get_promoted_products())


@main_bp.route("/goods/<int:id>")
def goods_page(id: int) -> ResponseValue:
    shirt: Optional[Goods] = db.session.query(Goods).options(joinedload(Goods.category),
                                                             joinedload(Goods.tags)).filter_by(id=id).first()
    if not shirt:
        flash(_("Product not found"), "danger")
        return redirect(url_for('main.index'))

    reviews = db.session.query(Review, User).join(User).filter(Review.goods_id == id).order_by(
        desc(Review.date)).limit(3).all()
    variants: List[Variant] = (
        db.session.query(Variant)
        .filter_by(goods_id=id)
        .all()
    )
    variant_options: Dict[str, List[str]] = {variant.name: [v.value for v in variants if v.name == variant.name] for
                                             variant in variants}

    user_id: int = current_user.id if current_user.is_authenticated else -1  # -1 is an invalid user ID
    in_wishlist: bool = False
    no_review: bool = True
    user_has_purchased: bool = False
    product_in_comparison: bool = False

    if current_user.is_authenticated:
        user_has_purchased = has_purchased(user_id, id)
        no_review = not db.session.query(exists().where(Review.user_id == user_id, Review.goods_id == id)).scalar()
        in_wishlist = db.session.query(exists().where(Wishlist.user_id == user_id, Wishlist.goods_id == id)).scalar()
        update_recently_viewed_products(user_id, id)

        comparison_history: Optional[ComparisonHistory] = (
            db.session.query(ComparisonHistory)
            .options(selectinload(ComparisonHistory.user))
            .filter_by(user_id=user_id)
            .order_by(desc(ComparisonHistory.timestamp))
            .first()
        )
        if comparison_history:
            product_in_comparison = id in json.loads(comparison_history.product_ids)

    related_products: List[Goods] = (
        db.session.query(Goods)
        .filter(
            Goods.category_id == shirt.category_id,
            Goods.id != shirt.id,
            Goods.stock > 0
        )
        .limit(3)
        .all()
    )

    return render_template("goods_page.html", shirt=shirt, reviews=reviews, average_rating=shirt.avg_rating,
                           user_has_purchased=user_has_purchased, no_review=no_review,
                           related_products=related_products, tags=shirt.tags,
                           variant_names=list(variant_options.keys()), in_wishlist=in_wishlist,
                           variant_options=variant_options, product_in_comparison=product_in_comparison)


@main_bp.route("/toggle-wishlist", methods=["POST"])
@login_required_with_message()
def toggle_wishlist() -> ResponseValue:
    goods_id: Optional[int] = request.form.get("goods_id", type=int)
    if not goods_id or not db.session.get(Goods, goods_id):
        flash(_("Invalid product ID"), "error")
        return redirect(url_for('main.index'))

    wishlist_item: Optional[Wishlist] = db.session.query(Wishlist).filter_by(user_id=current_user.id,
                                                                             goods_id=goods_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        message = _("Product removed from your wishlist.")
    else:
        new_wishlist_item = Wishlist(user_id=current_user.id, goods_id=goods_id)
        db.session.add(new_wishlist_item)
        message = _("Product added to your wishlist!")

    try:
        db.session.commit()
        flash(message, "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash(_("An error occurred while updating your wishlist. Please try again."), "error")

    return redirect(request.referrer or url_for('main.goods_page', id=goods_id))


@main_bp.route("/recommendations")
@login_required_with_message(redirect_back=True)
def recommendations() -> ResponseValue:
    user_id: int = current_user.id
    recently_viewed_products: List[RecentlyViewedProduct] = (
        db.session.query(RecentlyViewedProduct)
        .filter_by(user_id=user_id)
        .order_by(desc(RecentlyViewedProduct.timestamp))
        .limit(4)
        .all()
    )
    recs = get_recommended_products(user_id)
    return render_template("recommendations.html", recently_viewed_products=recently_viewed_products,
                           recommendations=recs)


@main_bp.route("/apply-discount", methods=["POST"])
@login_required_with_message()
def apply_discount() -> ResponseValue:
    discount_code: str = request.form.get("discount_code", type=str, default="")
    if not discount_code:
        flash(_("Please enter a discount code."), "warning")
        return redirect(url_for('carts.cart'))

    discount_applied: str = apply_discount_code(discount_code)
    if discount_applied == "success":
        flash(_("Discount code applied successfully."), "success")
    elif discount_applied == "already_used":
        flash(_("You have already used this discount code."), "danger")
    else:
        flash(_("Invalid discount code."), "danger")
    return redirect(url_for('carts.cart'))


@main_bp.route("/terms")
def terms() -> ResponseValue:
    return render_template("auth/terms.html")


@main_bp.route("/return-policy")
def return_policy() -> ResponseValue:
    return render_template("auth/return_policy.html")


@main_bp.route("/contact-us")
def contact_us() -> ResponseValue:
    return render_template("contact_us.html")


@main_bp.route("/faq")
def faq() -> ResponseValue:
    return render_template("faq.html")


@main_bp.route('/robots.txt')
def robots() -> ResponseValue:
    return send_from_directory('static', 'robots.txt')


def init_main(app: Flask) -> None:
    app.register_blueprint(main_bp, url_prefix='/')
