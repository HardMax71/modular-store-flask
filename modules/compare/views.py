import json

from flask import Blueprint, redirect, request, url_for, flash, render_template
from flask_babel import gettext as _
from flask_login import current_user

from modules.db.database import db
from modules.db.models import Goods, ComparisonHistory
from modules.decorators import login_required_with_message

compare_bp = Blueprint('compare', __name__)


@compare_bp.route("/compare")
@login_required_with_message()
def compare_products():
    comparison_history = ComparisonHistory.query.filter_by(user_id=current_user.id).first()

    if comparison_history:
        product_ids = json.loads(comparison_history.product_ids)
        products = db.session.query(Goods).filter(Goods.id.in_(product_ids)).all()
    else:
        products = []

    return render_template("product_comparison.html", products=products)


@compare_bp.route("/remove-from-comparison", methods=["POST"])
@login_required_with_message()
def remove_from_comparison():
    goods_id = request.form.get("goods_id", type=int)
    comparison_history = db.session.query(ComparisonHistory).filter_by(user_id=current_user.id).first()

    if comparison_history:
        product_ids = json.loads(comparison_history.product_ids)
        if goods_id in product_ids:
            product_ids.remove(goods_id)
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
def add_to_comparison():
    goods_id = request.form.get("goods_id", type=int)
    product = db.session.query(Goods).get(goods_id)

    if product:
        comparison_history = db.session.query(ComparisonHistory).filter_by(user_id=current_user.id).first()

        if comparison_history:
            product_ids = json.loads(comparison_history.product_ids)
            if goods_id not in product_ids:
                if len(product_ids) >= 3:
                    flash(_("You can only compare up to 3 products at a time."), "warning")
                else:
                    product_ids.append(goods_id)
                    comparison_history.product_ids = json.dumps(product_ids)
                    db.session.commit()
                    flash(_("Product added to comparison."), "success")
            else:
                flash(_("Product is already in comparison."), "info")
        else:
            new_comparison_history = ComparisonHistory(user_id=current_user.id, product_ids=json.dumps([goods_id]))
            db.session.add(new_comparison_history)
            db.session.commit()
            flash(_("Product added to comparison."), "success")
    else:
        flash(_("Product not found"), "error")

    return redirect(url_for('main.goods_page', id=goods_id))


def init_compare(app):
    app.register_blueprint(compare_bp)
