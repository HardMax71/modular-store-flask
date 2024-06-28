import json
from math import ceil

from flask import Blueprint, render_template, request, flash, redirect, url_for, session
from flask import send_from_directory
from flask_babel import gettext as _
from flask_login import current_user
from sqlalchemy import exists
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
def index():
    if 'filter_options' not in session:
        session['filter_options'] = get_filter_options()

    page = request.args.get('page', 1, type=int)
    shirts_query = filter_products(None, None, None).options(joinedload(Goods.tags))
    paginated_query, in_total, total_pages, per_page = paginate_query(shirts_query, page)

    return render_template("index.html", shirts=paginated_query, current_page=page, total_pages=total_pages,
                           categories=get_categories(), promoted_products=get_promoted_products(), per_page=per_page,
                           in_total=in_total)


@main_bp.route("/search")
def search_route():
    query = request.args.get('query')
    page = request.args.get('page', 1, type=int)
    per_page = AppConfig.PER_PAGE

    search_query = filter_products(name_query=query)
    total = search_query.count()
    offset = (page - 1) * per_page
    paginated_shirts = search_query.offset(offset).limit(per_page).all()
    total_pages = ceil(total / per_page)

    return render_template("index.html", shirts=paginated_shirts, query=query, total_pages=total_pages,
                           current_page=page, per_page=per_page, in_total=total, categories=get_categories(),
                           promoted_products=get_promoted_products(), )


@main_bp.route("/goods/<int:id>")
def goods_page(id):
    shirt = Goods.query.options(joinedload(Goods.category), joinedload(Goods.tags)).get(id)
    if not shirt:
        flash(_("Product not found"), "danger")
        return redirect(url_for('main.index'))

    reviews = db.session.query(Review, User).join(User).filter(Review.goods_id == id).order_by(Review.date.desc()).all()
    variants = Variant.query.filter_by(goods_id=id).all()
    variant_options = {variant.name: [v.value for v in variants if v.name == variant.name] for variant in variants}

    user_id = current_user.id if current_user.is_authenticated else None
    in_wishlist = False
    no_review = True
    user_has_purchased = False
    product_in_comparison = False

    if current_user.is_authenticated:
        user_has_purchased = has_purchased(user_id, id)
        no_review = not db.session.query(exists().where(Review.user_id == user_id, Review.goods_id == id)).scalar()
        in_wishlist = db.session.query(exists().where(Wishlist.user_id == user_id, Wishlist.goods_id == id)).scalar()
        update_recently_viewed_products(user_id, id)

        comparison_history = ComparisonHistory.query.options(selectinload(ComparisonHistory.user)).filter_by(
            user_id=user_id).order_by(ComparisonHistory.timestamp.desc()).first()
        if comparison_history:
            product_in_comparison = str(id) in json.loads(comparison_history.product_ids)

    related_products = Goods.query.filter(Goods.category_id == shirt.category_id, Goods.id != shirt.id,
                                          Goods.stock > 0).limit(3).all()

    return render_template("goods_page.html", shirt=shirt, reviews=reviews, average_rating=shirt.avg_rating,
                           user_has_purchased=user_has_purchased, no_review=no_review,
                           related_products=related_products, tags=shirt.tags,
                           variant_names=list(variant_options.keys()), in_wishlist=in_wishlist,
                           variant_options=variant_options, product_in_comparison=product_in_comparison)


@main_bp.route("/toggle-wishlist", methods=["POST"])
@login_required_with_message()
def toggle_wishlist():
    goods_id = request.form.get("goods_id", type=int)
    if not goods_id:
        flash(_("Invalid product ID"), "error")
        return redirect(url_for('main.index'))

    wishlist_item = db.session.query(Wishlist).filter_by(user_id=current_user.id, goods_id=goods_id).first()
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
def recommendations():
    user_id = current_user.id
    recently_viewed_products = RecentlyViewedProduct.query.filter_by(user_id=user_id).order_by(
        RecentlyViewedProduct.timestamp.desc()).limit(5).all()
    recs = get_recommended_products(user_id)
    return render_template("recommendations.html", recently_viewed_products=recently_viewed_products,
                           recommendations=recs)


@main_bp.route("/apply-discount", methods=["POST"])
@login_required_with_message()
def apply_discount():
    discount_code = request.form.get("discount_code")
    discount_applied = apply_discount_code(discount_code)
    if discount_applied == "success":
        flash(_("Discount code applied successfully."), "success")
    elif discount_applied == "already_used":
        flash(_("You have already used this discount code."), "danger")
    else:
        flash(_("Invalid discount code."), "danger")
    return redirect(url_for('carts.cart'))


@main_bp.route("/terms")
def terms():
    return render_template("auth/terms.html")


@main_bp.route("/return-policy")
def return_policy():
    return render_template("auth/return_policy.html")


@main_bp.route("/contact-us")
def contact_us():
    return render_template("contact_us.html")


@main_bp.route("/faq")
def faq():
    return render_template("faq.html")


@main_bp.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')
