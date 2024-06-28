import csv
import io
import json
from datetime import datetime, time
from io import StringIO, BytesIO
from typing import List, Dict, Any

import pandas as pd
from flask import Blueprint, flash, redirect, url_for
from flask import request, send_file
from flask_admin import Admin, AdminIndexView
from flask_admin import BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_babel import gettext as _
from flask_login import current_user
from markupsafe import Markup
from openpyxl import Workbook
from sqlalchemy import func
from sqlalchemy import inspect, text
from werkzeug.wrappers import Response
from ydata_profiling import ProfileReport

import config
from modules.db.database import db
from modules.db.models import RequestLog, Ticket, User, Goods, Category, Purchase, Review, Wishlist, Tag, \
    ProductPromotion, Discount, ShippingMethod, ReportedReview, TicketMessage
from modules.decorators import login_required_with_message, admin_required

# Create Blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def get_table_names():
    inspector = inspect(db.session.bind)
    return inspector.get_table_names()


# depiction of floats as e.g. 39.999..99 => "39.99"
def _number_formatter(view, context, model, name):
    value = getattr(model, name)
    if value is not None:
        return '{:.2f}'.format(value)
    return ''


class AdminView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        # Redirect to login page if user doesn't have access
        return redirect(url_for('login', next=request.url))


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    @login_required_with_message()
    @admin_required
    def index(self):
        if not current_user.is_admin:
            flash(_('You do not have permission to access this page.'), 'danger')
            return redirect(url_for('login'))
        return self.render('admin/index.html')


class TicketView(AdminView):
    column_searchable_list = ['user.username', 'title', 'description']
    column_filters = ['status', 'priority']
    column_editable_list = ['status', 'priority']
    form_excluded_columns = ['messages']

    column_formatters = {
        _('actions'): lambda v, c, m, p: Markup(
            f'<a href="{url_for("ticket_details", ticket_id=m.id)}" class="btn btn-primary btn-sm">{_("Details")}</a>'),
    }
    column_list = ['id', 'user.username', 'title', 'status', 'priority', 'created_at', 'actions']

    @expose('/assign/<int:ticket_id>', methods=['POST'])
    def assign_ticket(self, ticket_id):
        ticket = db.session.query(Ticket).get(ticket_id)
        if ticket:
            admin_id = request.form['admin_id']
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


class UserView(AdminView):
    column_searchable_list = ['username', 'email']
    column_filters = ['is_admin', 'is_active']
    column_editable_list = ['is_admin', 'is_active']
    form_excluded_columns = ['password']
    # hides password column from the user view
    column_exclude_list = ['password']


class StatisticsView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    @login_required_with_message()
    @admin_required
    def index(self):

        table_names = get_table_names()

        if request.method == 'POST':
            tables = request.form.getlist('tables')
            data_percentage = int(request.form.get('data_percentage', 100))

            profile_reports = []
            for table in tables:
                if table in table_names:
                    query = f"SELECT * FROM {table} ORDER BY id DESC LIMIT (SELECT CAST(COUNT(*) * {data_percentage / 100.0} AS INTEGER) FROM {table})"
                    df = pd.read_sql_query(query, db.session.bind)
                    profile = ProfileReport(df, title=f"{table.capitalize()} Dataset")
                    profile_reports.append(profile)

            if profile_reports:
                merged_report: ProfileReport = profile_reports[0]
                for report in profile_reports[1:]:
                    merged_report.add_report(report)

                profile_html = merged_report.to_html()

                output = io.BytesIO()
                output.write(profile_html.encode('utf-8'))
                output.seek(0)
                return send_file(output, mimetype='text/html', as_attachment=True,
                                 download_name='statistics_report.html')

        return self.render('admin/statistics.html', table_names=table_names)


class ReportsView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    @login_required_with_message()
    @admin_required
    def index(self):
        table_names = get_table_names()

        if request.method == 'POST':
            tables = request.form.getlist('tables')
            file_format = request.form.get('file_format')

            data = self.fetch_data(tables)

            if file_format == 'csv':
                return self.generate_csv(data)
            elif file_format == 'json':
                return self.generate_json(data)
            elif file_format == 'excel':
                return self.generate_excel(data)

        return self.render('admin/reports.html', table_names=table_names)

    def fetch_data(self, tables: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        data = {}
        for table in tables:
            if table in get_table_names():
                result = db.session.execute(text(f"SELECT * FROM {table}"))
                columns = result.keys()
                data[table] = [
                    {col: self.decode_if_bytes(value) for col, value in zip(columns, row)}
                    for row in result.fetchall()
                ]
        return data

    @staticmethod
    def decode_if_bytes(value: Any) -> Any:
        return value.decode('utf-8') if isinstance(value, bytes) else value

    def generate_csv(self, data: Dict[str, List[Dict[str, Any]]]) -> Response:
        output = StringIO()
        for table, rows in data.items():
            if rows:
                writer = csv.DictWriter(output, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                output.write('\n')
        output.seek(0)
        return send_file(
            BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv; charset=utf-8',
            as_attachment=True,
            download_name='data.csv'
        )

    def generate_json(self, data: Dict[str, List[Dict[str, Any]]]) -> Response:
        class CustomEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, bytes):
                    return obj.decode('utf-8')
                return super().default(obj)

        output = json.dumps(data, ensure_ascii=False, indent=2, cls=CustomEncoder)
        return send_file(
            BytesIO(output.encode('utf-8')),
            mimetype='application/json; charset=utf-8',
            as_attachment=True,
            download_name='data.json'
        )

    def generate_excel(self, data: Dict[str, List[Dict[str, Any]]]) -> Response:
        wb = Workbook()
        wb.remove(wb.active)  # Remove default sheet
        for table, rows in data.items():
            ws = wb.create_sheet(title=table)
            if rows:
                headers = list(rows[0].keys())
                ws.append(headers)
                for row in rows:
                    ws.append([row[header] for header in headers])
        output = BytesIO()
        wb.save(output)
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name='data.xlsx'
        )


class GoodsView(AdminView):
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

    def on_model_change(self, form, model, is_created):
        if not is_created and model.stock <= config.AppConfig.LOW_STOCK_THRESHOLD:
            goods_name = model.samplename
            notification_message = _(f"Low stock alert: {goods_name} is running low on stock.")

            # Flash a message to the current admin user
            flash(notification_message, "info")


class CategoryView(AdminView):
    column_searchable_list = ['name']
    form_excluded_columns = ['goods']
    form_ajax_refs = {
        'parent': {
            'fields': ['name'],
            'page_size': 10
        }
    }


class AnalyticsView(BaseView):
    @expose('/', methods=['GET', 'POST'])
    @login_required_with_message()
    @admin_required
    def index(self):
        if request.method == 'POST':
            start_date_str = request.form.get('start_date')
            end_date_str = request.form.get('end_date')

            # Convert start_date and end_date to datetime objects
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

            # Set the time component for start_date and end_date
            start_datetime = datetime.combine(start_date, time.min)
            end_datetime = datetime.combine(end_date, time.max)

            # Retrieve request logs within the specified date range
            request_logs_query = db.session.query(RequestLog).filter(
                RequestLog.timestamp >= start_datetime,
                RequestLog.timestamp <= end_datetime
            )

            total_requests = request_logs_query.count()
            request_logs = request_logs_query.limit(10).all()

            # Calculate analytics metrics for all logs in the selected range
            average_execution_time = 0
            status_code_counts = {}

            if total_requests > 0:
                # Calculate average execution time
                average_execution_time = (
                    request_logs_query.with_entities(func.avg(RequestLog.execution_time))
                    .scalar()
                )
                average_execution_time = f"{round(average_execution_time, 3)} s"

                # Calculate status code counts using grouping
                status_code_counts = dict(
                    request_logs_query.with_entities(
                        RequestLog.status_code, func.count(RequestLog.status_code)
                    )
                    .group_by(RequestLog.status_code)
                    .all()
                )

            # Render the template with the analytics data
            return self.render('admin/analytics.html', request_logs=request_logs, total_requests=total_requests,
                               average_execution_time=average_execution_time, status_code_counts=status_code_counts)

        return self.render('admin/analytics.html')


class PurchaseView(AdminView):
    column_searchable_list = ['user.username', 'date']
    column_filters = ['status']
    column_editable_list = ['status']
    form_excluded_columns = ['items']


class ReviewView(AdminView):
    column_searchable_list = ['user.username', 'goods.samplename']
    column_filters = ['moderated']
    column_editable_list = ['moderated']


class WishlistView(AdminView):
    column_searchable_list = ['user.username', 'goods.samplename']


class TagView(AdminView):
    column_searchable_list = ['name']
    form_excluded_columns = ['goods']


class ProductPromotionView(AdminView):
    form_excluded_columns = ['goods']


class DiscountView(AdminView):
    column_searchable_list = ['code']
    column_filters = ['start_date', 'end_date']
    form_excluded_columns = ['users']


class ShippingMethodView(AdminView):
    column_searchable_list = ['name']


class ReportedReviewView(AdminView):
    column_searchable_list = ['review.user.username', 'review.goods.samplename']
    column_filters = ['created_at']
    form_excluded_columns = ['user', 'review']
    column_formatters = {
        _('actions'): lambda v, c, m, p: Markup(
            f'<a href="{url_for("reported_review_detail", review_id=m.review_id)}" class="btn btn-primary btn-sm">{_("Details")}</a>'),
    }
    column_list = ['review_id', 'review.user.username', 'review.goods.samplename', 'explanation', 'created_at',
                   'actions']


############

# Create Admin instance
admin = Admin(name='Admin Panel', template_mode='bootstrap3', index_view=MyAdminIndexView())

# Add views to admin
admin.add_view(UserView(User, db.session, name='Users'))
admin.add_view(GoodsView(Goods, db.session, name='Goods'))
admin.add_view(CategoryView(Category, db.session, name='Categories'))
admin.add_view(PurchaseView(Purchase, db.session, name='Purchases'))
admin.add_view(ReviewView(Review, db.session, name='Reviews'))
admin.add_view(WishlistView(Wishlist, db.session, name='Wishlists'))
admin.add_view(TagView(Tag, db.session, name='Tags'))
admin.add_view(ProductPromotionView(ProductPromotion, db.session, name='Promotions'))
admin.add_view(DiscountView(Discount, db.session, name='Discounts'))
admin.add_view(ShippingMethodView(ShippingMethod, db.session, name='Shipping Methods'))
admin.add_view(ReportedReviewView(ReportedReview, db.session, name='Reported Reviews'))
admin.add_view(TicketView(Ticket, db.session, name='Tickets'))
admin.add_view(TicketMessageView(TicketMessage, db.session, name='Ticket Messages'))
admin.add_view(StatisticsView(name='Statistics', endpoint='statistics', category='Statistics'))
admin.add_view(ReportsView(name='Reports', endpoint='reports', category='Reports'))
admin.add_view(AnalyticsView(name='Analytics', endpoint='analytics', category='Reports'))


def init_admin(app):
    admin.init_app(app)
