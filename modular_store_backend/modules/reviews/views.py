# /modular_store_backend/modules/reviews/views.py
from typing import Optional

from flask import Blueprint, redirect, request, url_for, flash, render_template, Flask
from flask.typing import ResponseValue
from flask_babel import gettext as _
from flask_login import current_user

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Review, ReportedReview
from modular_store_backend.modules.decorators import login_required_with_message, admin_required
from modular_store_backend.modules.reviews.utils import (
    get_review, report_review_with_explanation, add_review_to_db, has_already_reviewed, has_purchased
)

reviews_bp = Blueprint('reviews', __name__)


@reviews_bp.route("/review/<int:review_id>/report", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to report a review."),
                             redirect_back=True)
def report_review(review_id: int) -> tuple[int, str] | ResponseValue:
    review: Optional[Review] = get_review(review_id)
    if not review:
        return 404, _("Review not found")

    explanation: Optional[str] = request.form.get("explanation", type=str)
    if not explanation:
        flash(_("Please provide an explanation for reporting the review."), "danger")
        return redirect(url_for("main.product_page", product_id=review.product_id))

    report_review_with_explanation(review.id, current_user.id, explanation)
    flash(_("Review reported. Thank you for your feedback."), "success")
    return redirect(url_for("main.product_page", product_id=review.product_id))


@reviews_bp.route("/add-review", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to review a product."))
def add_review() -> ResponseValue:
    user_id: int = current_user.id
    product_id: Optional[int] = request.form.get("product_id", type=int)
    if not product_id:
        flash(_("Invalid product ID"), "danger")
        return redirect(url_for('main.index'))

    if not has_purchased(user_id, product_id):
        flash(_("You must purchase the product before reviewing it."), "danger")
        return redirect(url_for('main.product_page', product_id=product_id))

    if has_already_reviewed(user_id, product_id):
        flash(_("You have already reviewed this product."), "danger")
        return redirect(url_for('main.product_page', product_id=product_id))

    review_data: dict[str, int | str] = {
        'user_id': user_id,
        'product_id': product_id,
        'rating': request.form.get("rating", type=int, default=5),
        'review': request.form["review"],
        'title': request.form["title"],
        'pros': request.form["pros"],
        'cons': request.form["cons"],
    }

    uploaded_images = request.files.getlist('images')

    add_review_to_db(review_data, uploaded_images)
    flash(_("Your review has been added!"), "success")
    return redirect(url_for('main.product_page', product_id=product_id))


@reviews_bp.route('/admin/reported-reviews')
@admin_required()
def reported_reviews() -> ResponseValue:
    all_reported_reviews: list[ReportedReview] = (
        db.session.query(ReportedReview)
        .all()
    )
    return render_template('admin/reported_reviews.html',
                           reported_reviews=all_reported_reviews)


@reviews_bp.route('/admin/reported-review/<int:review_id>')
@admin_required()
def reported_review_detail(review_id: int) -> ResponseValue:
    reported_review: Optional[ReportedReview] = (
        db.session.query(ReportedReview)
        .filter_by(review_id=review_id)
        .first()
    )
    review: Optional[Review] = db.session.get(Review, review_id)

    if reported_review and review:
        return render_template('admin/reported_review_detail.html',
                               reported_review=reported_review,
                               review=review)

    flash(_('Review not found.'), 'danger')
    return redirect(url_for('reviews.reported_reviews'))


@reviews_bp.route('/admin/reported-review/<int:review_id>/leave', methods=['POST'])
@admin_required()
def leave_review(review_id: int) -> ResponseValue:
    reports_to_delete: list[ReportedReview] = (
        db.session.query(ReportedReview)
        .filter_by(review_id=review_id)
        .all()
    )
    for report in reports_to_delete:
        db.session.delete(report)
    db.session.commit()
    flash(_('Review left as is.'), 'success')
    return redirect(url_for('reviews.reported_reviews'))


@reviews_bp.route('/admin/reported-review/<int:review_id>/delete', methods=['POST'])
@admin_required()
def delete_review(review_id: int) -> ResponseValue:
    review: Optional[Review] = db.session.get(Review, review_id)
    reports_to_delete: list[ReportedReview] = (
        db.session.query(ReportedReview)
        .filter_by(review_id=review_id)
        .all()
    )
    if review and reports_to_delete:
        for reported_review in reports_to_delete:
            db.session.delete(reported_review)
        db.session.delete(review)
        db.session.commit()
        flash(_('Review and reported reviews deleted.'), 'success')
    else:
        flash(_('Review not found.'), 'danger')
    return redirect(url_for('reviews.reported_reviews'))


def init_reviews(app: Flask) -> None:
    app.register_blueprint(reviews_bp, url_prefix='/reviews')
