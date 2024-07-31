# /modular_store_backend/modules/compare/views.py
import json
from typing import Optional

from flask import Blueprint, redirect, request, url_for, flash, render_template, Flask, current_app
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Product, ComparisonHistory
from modular_store_backend.modules.decorators import login_required_with_message

compare_bp = Blueprint('compare', __name__)


@compare_bp.route("/compare")
@login_required_with_message()
def compare_products() -> str:
    comparison_history: Optional[ComparisonHistory] = (
        db.session.query(ComparisonHistory)
        .filter_by(user_id=current_user.id)
        .first()
    )

    if comparison_history:
        product_ids = json.loads(comparison_history.product_ids)
        products = db.session.query(Product).filter(Product.id.in_(product_ids)).all()
    else:
        products = []

    return render_template("product_comparison.html", products=products)


@compare_bp.route("/remove-from-comparison", methods=["POST"])
@login_required_with_message()
def remove_from_comparison() -> ResponseValue:
    if comparison_history := db.session.query(ComparisonHistory).filter_by(user_id=current_user.id).first():
        product_ids = json.loads(comparison_history.product_ids)
        product_id: Optional[int] = request.form.get("product_id", type=int)
        if product_id and product_id in product_ids:
            product_ids.remove(product_id)
            if product_ids:
                comparison_history.product_ids = json.dumps(product_ids)
            else:
                db.session.delete(comparison_history)
            db.session.commit()
            flash(_("Product removed from comparison."), "success")
        else:
            flash(_("Product is not in comparison."), "info")
    else:
        flash(_("No products in comparison."), "info")

    return redirect(request.referrer or url_for('compare.compare_products'))


@compare_bp.route("/add-to-comparison", methods=["POST"])
@login_required_with_message()
def add_to_comparison() -> ResponseValue:
    product_id: Optional[int] = request.form.get("product_id", type=int)
    if not db.session.get(Product, product_id):
        flash(_("Product not found"), "error")
        return redirect(url_for('main.product_page', product_id=product_id))

    comparison_history: Optional[ComparisonHistory] = (
        db.session.query(ComparisonHistory)
        .filter_by(user_id=current_user.id)
        .first()
    )

    if comparison_history:
        product_ids = json.loads(comparison_history.product_ids)
        if product_id and product_id not in product_ids:
            if len(product_ids) >= current_app.config['MAX_COMPARE_STOCK_THRESHOLD']:
                flash(_("You can't compare so many products at a time."), "warning")
            else:
                product_ids.append(product_id)
                comparison_history.product_ids = json.dumps(product_ids)
                db.session.commit()
                flash(_("Product added to comparison."), "success")
        else:
            flash(_("Product is already in comparison."), "info")
    else:
        new_comparison_history: ComparisonHistory = ComparisonHistory(user_id=current_user.id,
                                                                      product_ids=json.dumps([product_id]))
        db.session.add(new_comparison_history)
        db.session.commit()
        flash(_("Product added to comparison."), "success")

    return redirect(url_for('main.product_page', product_id=product_id))


def init_compare(app: Flask) -> None:
    app.register_blueprint(compare_bp)
