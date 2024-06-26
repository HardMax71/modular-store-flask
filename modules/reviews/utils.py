import os
from werkzeug.utils import secure_filename

from modules.db.database import db_session
from modules.db.models import Review, Purchase, PurchaseItem, ReportedReview

def get_review(review_id):
    return Review.query.get(review_id)

def report_review_in_db(review_id, user_id, explanation):
    reported_review = ReportedReview(review_id=review_id, user_id=user_id, explanation=explanation)
    db_session.add(reported_review)
    db_session.commit()

def has_purchased(user_id, goods_id):
    purchase_item = PurchaseItem.query.join(Purchase).filter(
        Purchase.user_id == user_id,
        PurchaseItem.goods_id == goods_id
    ).first()
    return purchase_item is not None

def has_already_reviewed(user_id, goods_id):
    existing_review = Review.query.filter_by(user_id=user_id, goods_id=goods_id).first()
    return existing_review is not None

def handle_uploaded_images(files, upload_folder):
    images = []
    for file in files:
        if file.filename:
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            images.append(filename)
    return ','.join(images)

def add_review_to_db(review_data):
    new_review = Review(**review_data)
    db_session.add(new_review)
    db_session.commit()