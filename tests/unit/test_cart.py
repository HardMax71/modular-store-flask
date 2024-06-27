import unittest
from unittest.mock import patch, MagicMock

from modules.db.models import Cart, db_session, current_user


class TestCart(unittest.TestCase):
    @patch('modules.db.models.current_user')
    @patch('modules.db.models.db_session')
    def test_cart_info_empty(self, mock_db_session, mock_current_user):
        # Testing unregistered user with no items in cart
        mock_current_user.is_authenticated = False
        total_items, total_amount, discount_percentage = Cart.cart_info()
        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

        # Testing registered user with no items in cart
        mock_current_user.id = 1
        mock_query = MagicMock()
        mock_query.filter_by().first.return_value = MagicMock(total_items=0, subtotal=0)
        mock_db_session.query.return_value = mock_query

        total_items, total_amount, discount_percentage = Cart.cart_info()

        self.assertEqual(total_items, 0)
        self.assertEqual(total_amount, 0)
        self.assertEqual(discount_percentage, 0)

    @patch('modules.db.models.current_user')
    @patch('modules.db.models.db_session')
    def test_total_quantity(self, mock_db_session, mock_current_user):
        mock_current_user.is_authenticated = True
        mock_current_user.id = 1
        mock_query = MagicMock()
        mock_query.filter().scalar.return_value = 5
        mock_db_session.query.return_value = mock_query

        total_quantity = Cart.total_quantity()
        self.assertEqual(total_quantity, 5)


if __name__ == '__main__':
    unittest.main()
