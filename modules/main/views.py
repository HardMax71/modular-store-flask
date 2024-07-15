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
from modules.db.models import Product, ProductSelectionOption, Review, User, Wishlist, RecentlyViewedProduct, \
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
    products_query = filter_products(None, None, None).options(selectinload(Product.tags))
    paginated_query, in_total, total_pages, per_page = paginate_query(products_query, page)

    return render_template("index.html", products=paginated_query, current_page=page, total_pages=total_pages,
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
    paginated_products: List[Product] = search_query.offset(offset).limit(per_page).all()
    total_pages: int = ceil(total / per_page)

    return render_template("index.html", products=paginated_products, query=query,
                           total_pages=total_pages, current_page=page, per_page=per_page, in_total=total,
                           categories=get_categories(), promoted_products=get_promoted_products())


@main_bp.route("/products/<int:product_id>")
def product_page(product_id: int) -> ResponseValue:
    product: Optional[Product] = (db.session.query(Product)
                                  .options(joinedload(Product.category), selectinload(Product.tags))
                                  .filter_by(id=product_id)
                                  .first())
    if not product:
        flash(_("Product not found"), "danger")
        return redirect(url_for('main.index'))

    reviews = db.session.query(Review, User).join(User).filter(Review.product_id == product_id).order_by(
        desc(Review.date)).limit(3).all()
    selection_options: List[ProductSelectionOption] = (
        db.session.query(ProductSelectionOption)
        .filter_by(product_id=product_id)
        .all()
    )
    variant_options: Dict[str, List[str]] = {
        variant.name: [v.value for v in selection_options if v.name == variant.name] for
        variant in selection_options}

    user_id: int = current_user.id if current_user.is_authenticated else -1  # -1 is an invalid user ID
    in_wishlist: bool = False
    no_review: bool = True
    user_has_purchased: bool = False
    product_in_comparison: bool = False

    if current_user.is_authenticated:
        user_has_purchased = has_purchased(user_id, product_id)
        no_review = not db.session.query(
            exists().where(Review.user_id == user_id, Review.product_id == product_id)).scalar()
        in_wishlist = db.session.query(
            exists().where(Wishlist.user_id == user_id, Wishlist.product_id == product_id)).scalar()
        update_recently_viewed_products(user_id, product_id)

        comparison_history: Optional[ComparisonHistory] = (
            db.session.query(ComparisonHistory)
            .options(selectinload(ComparisonHistory.user))
            .filter_by(user_id=user_id)
            .order_by(desc(ComparisonHistory.timestamp))
            .first()
        )
        if comparison_history:
            product_in_comparison = product_id in json.loads(comparison_history.product_ids)

    related_products: List[Product] = (
        db.session.query(Product)
        .filter(
            Product.category_id == product.category_id,
            Product.id != product.id,
            Product.stock > 0
        )
        .limit(3)
        .all()
    )

    return render_template("product_page.html", product=product, reviews=reviews,
                           average_rating=product.avg_rating,
                           user_has_purchased=user_has_purchased, no_review=no_review,
                           related_products=related_products, tags=product.tags,
                           variant_names=list(variant_options.keys()), in_wishlist=in_wishlist,
                           variant_options=variant_options, product_in_comparison=product_in_comparison)


@main_bp.route("/toggle-wishlist", methods=["POST"])
@login_required_with_message()
def toggle_wishlist() -> ResponseValue:
    product_id: Optional[int] = request.form.get("product_id", type=int)
    if not product_id or not db.session.get(Product, product_id):
        flash(_("Invalid product ID"), "error")
        return redirect(url_for('main.index'))

    wishlist_item: Optional[Wishlist] = db.session.query(Wishlist).filter_by(user_id=current_user.id,
                                                                             product_id=product_id).first()
    if wishlist_item:
        db.session.delete(wishlist_item)
        message = _("Product removed from your wishlist.")
    else:
        new_wishlist_item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(new_wishlist_item)
        message = _("Product added to your wishlist!")

    try:
        db.session.commit()
        flash(message, "success")
    except SQLAlchemyError:
        db.session.rollback()
        flash(_("An error occurred while updating your wishlist. Please try again."), "error")

    return redirect(request.referrer or url_for('main.product_page', product_id=product_id))


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
