from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_babel import gettext as _
from flask_login import current_user, login_required

from modules.db.database import db_session
from modules.db.models import Ticket, TicketMessage

tickets_bp = Blueprint('tickets', __name__)


@tickets_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_ticket():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        priority = request.form['priority']

        new_ticket = Ticket(user_id=current_user.id, title=title, description=description, priority=priority)
        db_session.add(new_ticket)
        db_session.commit()

        flash(_('Ticket created successfully.'), 'success')
        return redirect(url_for('tickets.ticket_details', ticket_id=new_ticket.id))

    return render_template('tickets/create_ticket.html')


@tickets_bp.route('/')
@login_required
def list_tickets():
    user_tickets = db_session.query(Ticket).filter_by(user_id=current_user.id).order_by(
        Ticket.created_at.desc()).all()
    assigned_tickets = []
    if current_user.is_admin:
        assigned_tickets = db_session.query(Ticket).filter(Ticket.admin_id == current_user.id).order_by(
            Ticket.created_at.desc()).all()
    return render_template('tickets/list_tickets.html', user_tickets=user_tickets, assigned_tickets=assigned_tickets)


@tickets_bp.route('/<int:ticket_id>/update', methods=['POST'])
@login_required
def update_ticket(ticket_id):
    if not current_user.is_admin:
        flash(_('You do not have permission to perform this action.'), 'danger')
        return redirect(url_for('tickets.ticket_details', ticket_id=ticket_id))

    ticket = db_session.query(Ticket).get(ticket_id)
    if not ticket:
        flash(_('Ticket not found.'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    ticket.status = request.form['status']
    ticket.priority = request.form['priority']
    ticket.title = request.form['title']
    ticket.description = request.form['description']
    db_session.commit()

    flash(_('Ticket updated successfully.'), 'success')
    return redirect(url_for('tickets.ticket_details', ticket_id=ticket_id))


@tickets_bp.route('/<int:ticket_id>', methods=['GET', 'POST'])
@login_required
def ticket_details(ticket_id):
    ticket = db_session.query(Ticket).get(ticket_id)
    if not ticket or (ticket.user_id != current_user.id and not current_user.is_admin):
        flash(_('Ticket not found or you do not have permission to view it.'), 'danger')
        return redirect(url_for('tickets.list_tickets'))

    if request.method == 'POST':
        message = request.form['message']
        is_admin = current_user.is_admin
        new_message = TicketMessage(ticket_id=ticket_id, user_id=current_user.id, message=message,
                                    is_admin=is_admin)
        db_session.add(new_message)
        db_session.commit()
        flash(_('Message sent successfully.'), 'success')

    messages = db_session.query(TicketMessage).filter_by(ticket_id=ticket_id).order_by(
        TicketMessage.created_at.asc()).all()
    return render_template('tickets/ticket_details.html', ticket=ticket, messages=messages)


def init_tickets(app):
    app.register_blueprint(tickets_bp, url_prefix='/tickets')
