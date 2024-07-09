from typing import Optional

from flask import Blueprint, render_template, request, flash, redirect, url_for, Flask
from flask_babel import gettext as _
from flask_login import current_user, login_required
from werkzeug.wrappers import Response

from modules.db.database import db
from modules.db.models import Ticket, TicketMessage

tickets_bp = Blueprint('tickets', __name__)


@tickets_bp.route('/create', methods=['GET', 'POST'])
@login_required  # type: ignore
def create_ticket() -> Response | str:
    if request.method == 'POST':
        title = request.form.get('title', type=str, default="No title")
        description = request.form.get('description', type=str, default="No description")
        priority = request.form.get('priority', type=int, default=1)

        new_ticket = Ticket(user_id=current_user.id, title=title, description=description, priority=priority)
        db.session.add(new_ticket)
        db.session.commit()

        flash(_('Ticket created successfully.'), 'success')
        return redirect(url_for('tickets.ticket_details', ticket_id=new_ticket.id))

    return render_template('tickets/create_ticket.html')


@tickets_bp.route('/')
@login_required  # type: ignore
def list_tickets() -> Response | str:
    user_tickets: list[Ticket] = (
        db.session.query(Ticket)
        .filter(Ticket.user_id == current_user.id)
        .order_by(Ticket.created_at.desc())
        .all()
    )
    assigned_tickets = []
    if current_user.is_admin:
        assigned_tickets = db.session.query(Ticket).filter(Ticket.admin_id == current_user.id).order_by(
            Ticket.created_at.desc()).all()
    return render_template('tickets/list_tickets.html', user_tickets=user_tickets, assigned_tickets=assigned_tickets)


@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required  # type: ignore
def update_ticket(ticket_id: int) -> Response:
    if not current_user.is_admin:
        flash(_('You do not have permission to perform this action.'), 'danger')
        return redirect(url_for('tickets.ticket_details', ticket_id=ticket_id))

    ticket: Optional[Ticket] = db.session.get(Ticket, ticket_id)
    if not ticket:
        flash(_('Ticket not found.'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    ticket.status = request.form.get('status', 'open')
    ticket.priority = request.form.get('priority', 'normal')
    ticket.title = request.form.get('title', 'No title')
    ticket.description = request.form.get('description', 'No description')
    db.session.commit()

    flash(_('Ticket updated successfully.'), 'success')
    return redirect(url_for('tickets.ticket_details', ticket_id=ticket_id))


@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required  # type: ignore
def ticket_details(ticket_id) -> Response | str:
    ticket: Optional[Ticket] = db.session.get(Ticket, ticket_id)
    if not ticket or (ticket.user_id != current_user.id and not current_user.is_admin):
        flash(_('Ticket not found or you do not have permission to view it.'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    if request.method == 'POST':
        message = request.form['message']
        is_admin = current_user.is_admin
        new_message = TicketMessage(ticket_id=ticket_id, user_id=current_user.id, message=message,
                                    is_admin=is_admin)
        db.session.add(new_message)
        db.session.commit()
        flash(_('Message sent successfully.'), 'success')

    messages = db.session.query(TicketMessage).filter_by(ticket_id=ticket_id).order_by(
        TicketMessage.created_at.asc()).all()
    return render_template('tickets/ticket_details.html', ticket=ticket, messages=messages)


def init_tickets(app: Flask) -> None:
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
