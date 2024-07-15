import io
import os
import tempfile
import zipfile
from datetime import datetime, time
from pathlib import Path
from typing import List, Dict, Any, Union

import pandas as pd
from flask import Blueprint, Flask
from flask import current_app, request, flash, redirect, url_for
from flask import send_file
from flask.typing import ResponseValue
from flask_admin import Admin, AdminIndexView
from flask_admin import BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.model.base import ViewArgs
from flask_babel import gettext as _
from flask_login import current_user
from flask_wtf import FlaskForm
from markupsafe import Markup
from sqlalchemy import func, Integer
from sqlalchemy import inspect, select, Table
from sqlalchemy.orm import aliased
from werkzeug.utils import secure_filename
from wtforms import StringField, TextAreaField, SubmitField, FileField
from wtforms.validators import DataRequired
from ydata_profiling import ProfileReport  # type: ignore

import config
from modules.admin.utils import generate_csv, generate_json, generate_excel
from modules.db.database import db, Base, Database
from modules.db.models import RequestLog, Ticket, User, Product, Category, Purchase, Review, Wishlist, Tag, \
    ProductPromotion, Discount, ShippingMethod, ReportedReview, TicketMessage
from modules.decorators import login_required_with_message, admin_required
from modules.email import send_email

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_table_names() -> List[str]:
    inspector = inspect(db.session.bind)
    if not inspector:
        return []
    return inspector.get_table_names()  # type: ignore


def _number_formatter(view: Any, context: Any, model: Any, name: str) -> str:
    value = getattr(model, name)
    if value is not None:
        return '{:.2f}'.format(value)
    return ''


class AdminView(ModelView):  # type: ignore
    def is_accessible(self) -> bool:
        return (current_user.is_authenticated and current_user.is_admin) or False

    def inaccessible_callback(self, name: str, **kwargs: Any) -> ResponseValue:
        return redirect(url_for('login', next=request.url))


class MyAdminIndexView(AdminIndexView):  # type: ignore
    @expose('/')  # type: ignore
    @login_required_with_message()
    @admin_required()
    def index(self) -> ResponseValue:
        if not current_user.is_admin:
            flash(_('You do not have permission to access this page.'), 'danger')
            return redirect(url_for('login'))
        return self.render('admin/index.html')  # type: ignore


class TicketView(AdminView):
    column_searchable_list: list[str] = ['user.username', 'title', 'description']
    column_filters: list[str] = ['status', 'priority']
    column_editable_list: list[str] = ['status', 'priority']
    form_excluded_columns: list[str] = ['messages']

    column_formatters = {
        _('actions'): lambda v, c, m, p: Markup(
            f'<a href="{url_for("tickets.ticket_details", ticket_id=m.id)}" '
            f'class="btn btn-primary btn-sm">{_("Details")}</a>'),
    }
    column_list: list[str] = ['id', 'user.username', 'title', 'status', 'priority', 'created_at', 'actions']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Tickets Management')
        return view_args

    @expose('/assign/<int:ticket_id>', methods=['POST'])  # type: ignore
    def assign_ticket(self, ticket_id: int) -> ResponseValue:
        if ticket := db.session.get(Ticket, ticket_id):
            admin_id = request.form.get('admin_id', type=int)
            ticket.admin_id = admin_id
            db.session.commit()
            flash(_('Ticket assigned successfully.'), 'success')
        else:
            flash(_('Ticket not found.'), 'danger')
        return redirect(url_for('ticket.index_view'))


class TicketMessageView(AdminView):
    column_searchable_list = ['user.username', 'message']
    column_filters = ['is_admin']
    form_excluded_columns = ['user', 'ticket']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Ticket Messages')
        return view_args


class UserView(AdminView):
    column_searchable_list = ['username', 'email']
    column_filters = ['is_admin', 'is_active']
    column_editable_list = ['is_admin', 'is_active']
    form_excluded_columns = ['password']
    # hides password column from the user view
    column_exclude_list = ['password']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Users Management')
        return view_args


class StatisticsView(BaseView):  # type: ignore
    @expose('/', methods=['GET', 'POST'])  # type: ignore
    @login_required_with_message()
    @admin_required()
    def index(self) -> ResponseValue:
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        if request.method == 'POST':
            tables = request.form.getlist('tables')
            data_percentage = int(request.form.get('data_percentage', 100))

            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w') as zf:
                for table_name in tables:
                    if table_name in table_names:
                        table = Table(table_name, db.metadata, autoload_with=db.engine)
                        aliased_table = aliased(table)

                        count_subq = select(func.count()).select_from(table).scalar_subquery()
                        limit = select(func.cast(count_subq * (data_percentage / 100.0), Integer)).scalar_subquery()

                        query = (
                            select(aliased_table)
                            .order_by(aliased_table.c.id.desc())
                            .limit(limit)
                        )

                        df = pd.read_sql(query, db.engine)
                        profile = ProfileReport(df, title=f"{table_name.capitalize()} Dataset")

                        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as tmp:
                            profile.to_file(tmp.name)
                        with open(tmp.name, 'rb') as f:
                            zf.writestr(f"{table_name}_report.html", f.read())
                        Path(tmp.name).unlink()

            memory_file.seek(0)
            return send_file(
                memory_file,
                mimetype='application/zip',
                as_attachment=True,
                download_name='statistics_reports.zip'
            )

        return self.render('admin/statistics.html', table_names=table_names)  # type: ignore


class ReportsView(BaseView):  # type: ignore
    @expose('/', methods=['GET', 'POST'])  # type: ignore
    @login_required_with_message()
    @admin_required()
    def index(self) -> ResponseValue:
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()

        if request.method == 'POST':
            tables = request.form.getlist('tables')
            file_format = request.form.get('file_format')

            data = self.fetch_data(tables)

            if file_format == 'csv':
                return generate_csv(data)
            elif file_format == 'json':
                return generate_json(data)
            elif file_format == 'excel':
                return generate_excel(data)

        return self.render('admin/reports.html', table_names=table_names)  # type: ignore

    def fetch_data(self, tables: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        inspector = inspect(db.engine)
        all_table_names = inspector.get_table_names()
        data = {}

        for table_name in tables:
            if table_name in all_table_names:
                table = Table(table_name, Base.metadata, autoload_with=db.engine)
                aliased_table = aliased(table)
                query = select(aliased_table)
                with db.engine.connect() as connection:
                    result = connection.execute(query)
                    columns = result.keys()
                    data[table_name] = [
                        {col: self.decode_if_bytes(value) for col, value in zip(columns, row)}
                        for row in result.fetchall()
                    ]
        return data

    @staticmethod
    def decode_if_bytes(value: Any) -> Any:
        return value.decode('utf-8') if isinstance(value, bytes) else value


class ProductsViews(AdminView):
    column_searchable_list = ['samplename', 'description']
    column_filters = ['onSale', 'category']
    column_editable_list = ['price', 'onSale', 'onSalePrice', 'stock']
    form_excluded_columns = ['purchase_items', 'reviews', 'wishlist_items', 'cart_items', 'recently_viewed_by']
    form_widget_args = {
        'description': {'rows': 10},
    }
    form_ajax_refs = {
        'category': {
            'fields': ['name'],
            'page_size': 10
        },
        'tags': {
            'fields': ['name'],
            'page_size': 10
        },
        'related_products': {
            'fields': ['samplename'],
            'page_size': 10
        }
    }

    column_formatters = {
        'price': _number_formatter,
        'onSalePrice': _number_formatter,
    }

    def on_model_change(self, form: Any, model: Product, is_created: bool) -> None:
        if not is_created and model.stock <= config.AppConfig.LOW_STOCK_THRESHOLD:
            product_name: str = model.samplename or 'Unknown Product'
            notification_message = _(f"Low stock alert: {product_name} is running low on stock.")

            # Flash a message to the current admin user
            flash(notification_message, "info")


class CategoryView(AdminView):
    column_searchable_list = ['name']
    form_excluded_columns = ['product']
    form_ajax_refs = {
        'parent': {
            'fields': ['name'],
            'page_size': 10
        }
    }


class AnalyticsView(BaseView):  # type: ignore
    @expose('/', methods=['GET', 'POST'])  # type: ignore
    @login_required_with_message()
    @admin_required()
    def index(self) -> ResponseValue:
        if request.method == 'POST':
            start_date_str: str = request.form.get('start_date', type=str,
                                                   default=datetime.today().strftime('%Y-%m-%d'))
            end_date_str: str = request.form.get('end_date', type=str, default=datetime.today().strftime('%Y-%m-%d'))

            # Convert start_date and end_date to datetime objects
            start_date: datetime = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date: datetime = datetime.strptime(end_date_str, '%Y-%m-%d')

            # Set the time component for start_date and end_date
            start_datetime: datetime = datetime.combine(start_date, time.min)
            end_datetime: datetime = datetime.combine(end_date, time.max)

            # Retrieve request logs within the specified date range
            request_logs_query = db.session.query(RequestLog).filter(
                RequestLog.timestamp >= start_datetime,
                RequestLog.timestamp <= end_datetime
            )

            total_requests: int = request_logs_query.count()
            request_logs: List[RequestLog] = request_logs_query.limit(10).all()

            # Calculate analytics metrics for all logs in the selected range
            average_execution_time: Union[int, str] = 0
            status_code_counts: Dict[int, int] = {}

            if total_requests > 0:
                # Calculate average execution time
                avg_execution_time: float = request_logs_query.with_entities(
                    func.avg(RequestLog.execution_time)).scalar() or 0.0
                average_execution_time = f"{round(avg_execution_time, 3)} s"

                # Calculate status code counts using grouping
                status_code_counts = dict(
                    (row[0], row[1]) for row in request_logs_query.with_entities(
                        RequestLog.status_code, func.count(RequestLog.status_code)
                    )
                    .group_by(RequestLog.status_code)
                    .all()
                )

            # Render the template with the analytics data
            return self.render('admin/analytics.html',  # type: ignore[no-any-return]
                               request_logs=request_logs,
                               total_requests=total_requests,
                               average_execution_time=average_execution_time,
                               status_code_counts=status_code_counts)

        return self.render('admin/analytics.html')  # type: ignore


class PurchaseView(AdminView):
    column_searchable_list = ['user.username', 'date']
    column_filters = ['status']
    column_editable_list = ['status']
    form_excluded_columns = ['items']


class ReviewView(AdminView):
    column_searchable_list = ['user.username', 'products.samplename']
    column_filters = ['moderated']
    column_editable_list = ['moderated']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Reviews Management')
        return view_args


class WishlistView(AdminView):
    column_searchable_list = ['user.username', 'product.samplename']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Wishlists Management')
        return view_args


class TagView(AdminView):
    column_searchable_list = ['name']
    form_excluded_columns = ['product']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Tags Management')
        return view_args


class ProductPromotionView(AdminView):
    form_excluded_columns = ['product']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Promotions')
        return view_args


class DiscountView(AdminView):
    column_searchable_list = ['code']
    column_filters = ['start_date', 'end_date']
    form_excluded_columns = ['users']


class ShippingMethodView(AdminView):
    column_searchable_list = ['name']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Shipping Methods')
        return view_args


class ReportedReviewView(AdminView):
    page_title = _('Reported Reviews')
    column_searchable_list = ['review.user.username', 'review.products.samplename']
    column_filters = ['created_at']
    form_excluded_columns = ['user', 'review']
    column_formatters = {
        _('actions'): lambda v, c, m, p: Markup(
            f'<a href="{url_for("reviews.reported_review_detail", review_id=m.review_id)}'
            f'" class="btn btn-primary btn-sm">{_("Details")}</a>'),
    }
    column_list = ['review_id', 'review.user.username', 'review.products.samplename', 'explanation', 'created_at',
                   'actions']

    def _get_list_extra_args(self) -> ViewArgs:
        view_args = super()._get_list_extra_args()
        view_args.extra_args["page_title"] = _('Reported Reviews')
        return view_args


class EmailForm(FlaskForm):  # type: ignore
    subject = StringField(_('Subject'), validators=[DataRequired()])
    body = TextAreaField(_('Body'), validators=[DataRequired()])
    attachments = FileField(_('Attachments'))
    submit = SubmitField(_('Send Email'))


class EmailView(BaseView):  # type: ignore
    @expose('/', methods=['GET', 'POST'])
    @login_required_with_message()
    @admin_required()
    def index(self, cls=None):  # type: ignore
        form = EmailForm()
        if form.validate_on_submit():
            if not form.subject.data or not form.body.data:
                flash(_('Subject and body are required'), 'danger')
                return redirect(url_for('admin.send_emails'))

            subject: str = form.subject.data
            body: str = form.body.data

            attachments = []
            for file in request.files.getlist('attachments'):
                if file.filename:
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    attachments.append(file_path)

            users = db.session.query(User).filter_by(email_notifications_enabled=True).all()
            try:
                for user in users:
                    if user.email:
                        send_email(user.email, subject, body, attachments)
                flash(_('Emails sent successfully'), 'success')
            except Exception as e:
                flash(_('Error sending emails: %(error)', error=str(e)), 'danger')
            finally:
                return redirect(url_for('admin.index'))
        return self.render('admin/send_email.html', form=form)


############
def init_admin(app: Flask) -> None:
    admin = Admin(name='Admin Panel', template_mode='bootstrap4', index_view=MyAdminIndexView())
    init_admin_views(admin, db)
    admin.init_app(app)


# Add views to admin
def init_admin_views(admin: Admin, database: Database) -> None:
    admin.add_view(UserView(User, database.session, name='Users'))
    admin.add_view(ProductsViews(Product, database.session, name='Products'))
    admin.add_view(CategoryView(Category, database.session, name='Categories'))
    admin.add_view(PurchaseView(Purchase, database.session, name='Purchases'))
    admin.add_view(ReviewView(Review, database.session, name='Reviews'))
    admin.add_view(WishlistView(Wishlist, database.session, name='Wishlists'))
    admin.add_view(TagView(Tag, database.session, name='Tags'))
    admin.add_view(ProductPromotionView(ProductPromotion, database.session, name='Promotions'))
    admin.add_view(DiscountView(Discount, database.session, name='Discounts'))
    admin.add_view(ShippingMethodView(ShippingMethod, database.session, name='Shipping Methods'))
    admin.add_view(ReportedReviewView(ReportedReview, database.session, name='Reported Reviews'))
    admin.add_view(TicketView(Ticket, database.session, name='Tickets'))
    admin.add_view(TicketMessageView(TicketMessage, database.session, name='Ticket Messages'))
    admin.add_view(StatisticsView(name='Statistics', endpoint='statistics', category='Statistics'))
    admin.add_view(ReportsView(name='Reports', endpoint='reports', category='Reports'))
    admin.add_view(AnalyticsView(name='Analytics', endpoint='analytics', category='Reports'))
    admin.add_view(EmailView(name='Send Emails', endpoint='send_emails', category='Marketing'))
