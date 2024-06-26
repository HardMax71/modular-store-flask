from flask import Blueprint, redirect, request, url_for, flash, render_template
from flask_babel import gettext as _
from flask_login import current_user

from config import AppConfig
from modules.db.database import db_session
from modules.db.models import Review, ReportedReview
from modules.decorators import login_required_with_message, admin_required
from .utils import (
    get_review, report_review_in_db, has_purchased, has_already_reviewed,
    handle_uploaded_images, add_review_to_db
)

reviews_bp = Blueprint('reviews', __name__)


@reviews_bp.route("/review/<int:review_id>/report", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to report a review."))
def report_review(review_id):
    review = get_review(review_id)
    if not review:
        return 404, _("Review not found")

    explanation = request.form.get("explanation")
    if not explanation:
        flash(_("Please provide an explanation for reporting the review."), "danger")
        return redirect(url_for("main.goods_page", id=review.goods_id))

    report_review_in_db(review.id, current_user.id, explanation)
    flash(_("Review reported. Thank you for your feedback."), "success")
    return redirect(url_for("main.goods_page", id=review.goods_id))


@reviews_bp.route("/add-review", methods=["POST"])
@login_required_with_message(message=_("You must be logged in to review a product."))
def add_review():
    user_id = current_user.id
    goods_id = request.form["goods_id"]

    if not has_purchased(user_id, goods_id):
        flash(_("You must purchase the product before reviewing it."), "danger")
        return redirect(url_for('main.goods_page', id=goods_id))

    if has_already_reviewed(user_id, goods_id):
        flash(_("You have already reviewed this product."), "danger")
        return redirect(url_for('main.goods_page', id=goods_id))

    review_data = {
        'user_id': user_id,
        'goods_id': goods_id,
        'rating': request.form["rating"],
        'review': request.form["review"],
        'title': request.form["title"],
        'pros': request.form["pros"],
        'cons': request.form["cons"],
        'images': handle_uploaded_images(request.files.getlist('images'), AppConfig.REVIEW_PICS_FOLDER)
    }

    add_review_to_db(review_data)
    flash(_("Your review has been added!"), "success")
    return redirect(url_for('main.goods_page', id=goods_id))


@reviews_bp.route('/admin/reported-reviews')
@login_required_with_message()
@admin_required
def reported_reviews():
    reported_reviews = ReportedReview.query.all()
    return render_template('admin/reported_reviews.html', reported_reviews=reported_reviews)


@reviews_bp.route('/admin/reported-review/<int:review_id>')
@login_required_with_message()
@admin_required
def reported_review_detail(review_id):
    reported_review = ReportedReview.query.filter_by(review_id=review_id).first()
    review = Review.query.get(review_id)

    if reported_review and review:
        return render_template('admin/reported_review_detail.html', reported_review=reported_review, review=review)

    flash(_('Review not found.'), 'danger')
    return redirect(url_for('reviews.reported_reviews'))


@reviews_bp.route('/admin/reported-review/<int:review_id>/leave', methods=['POST'])
@login_required_with_message()
@admin_required
def leave_review(review_id):
    reported_reviews = ReportedReview.query.filter_by(review_id=review_id).all()
    for reported_review in reported_reviews:
        db_session.delete(reported_review)
    db_session.commit()
    flash(_('Review left as is.'), 'success')
    return redirect(url_for('reviews.reported_reviews'))


@reviews_bp.route('/admin/reported-review/<int:review_id>/delete', methods=['POST'])
@login_required_with_message()
@admin_required
def delete_review(review_id):
    review = Review.query.get(review_id)
    reported_reviews = ReportedReview.query.filter_by(review_id=review_id).all()
    if review and reported_reviews:
        for reported_review in reported_reviews:
            db_session.delete(reported_review)
        db_session.delete(review)
        db_session.commit()
        flash(_('Review and reported reviews deleted.'), 'success')
    else:
        flash(_('Review not found.'), 'danger')
    return redirect(url_for('reviews.reported_reviews'))


def init_reviews(app):
    app.register_blueprint(reviews_bp, url_prefix='/reviews')
