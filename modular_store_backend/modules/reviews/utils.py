import os
from typing import List, Optional

from flask import current_app
from sqlalchemy import and_
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from modular_store_backend.modules.db.database import db
from modular_store_backend.modules.db.models import Purchase, PurchaseItem, ReportedReview, Review, ReviewImage


def get_review(review_id: int) -> Optional[Review]:
    return db.session.get(Review, review_id)


def report_review_in_db(review_id: int, user_id: int, explanation: str) -> None:
    reported_review = ReportedReview(review_id=review_id, user_id=user_id, explanation=explanation)
    db.session.add(reported_review)
    db.session.commit()


def has_purchased(user_id: int, product_id: int) -> bool:
    purchase_item: Optional[PurchaseItem] = (
        db.session.query(PurchaseItem)
        .join(Purchase, and_(
            Purchase.id == PurchaseItem.purchase_id,
            Purchase.user_id == user_id
        ))
        .filter(PurchaseItem.product_id == product_id)
        .first()
    )
    return purchase_item is not None


def has_already_reviewed(user_id: int, product_id: int) -> bool:
    existing_review: Optional[Review] = (
        db.session.query(Review)
        .filter(Review.user_id == user_id,
                Review.product_id == product_id)
        .first()
    )
    return existing_review is not None


def handle_uploaded_images(files: List[FileStorage], upload_folder: str) -> List[str]:
    images = []
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)
            images.append(filename)
    return images


def allowed_file(filename: str) -> bool:
    if '.' in filename:
        file_extension = '.' + filename.rsplit('.', 1)[1].lower()
        return file_extension in current_app.config['IMG_FORMATS']
    return False


def add_review_to_db(review_data: dict[str, int | str], images: List[FileStorage]) -> None:
    new_review = Review(
        user_id=review_data['user_id'],
        product_id=review_data['product_id'],
        rating=review_data['rating'],
        review=review_data['review'],
        title=review_data['title'],
        pros=review_data['pros'],
        cons=review_data['cons']
    )
    db.session.add(new_review)
    db.session.flush()

    uploaded_images = handle_uploaded_images(images, upload_folder=current_app.config['REVIEW_PICS_FOLDER'])

    for image_filename in uploaded_images:
        review_image = ReviewImage(review_id=new_review.id, _image=image_filename)
        db.session.add(review_image)

    db.session.commit()
