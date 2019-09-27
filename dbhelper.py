# This class serves the SQL commands

# Production mode
import os
import psycopg2

DATABASE_URL = os.environ['DATABASE_URL']

class DBHelper:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        self.cursor = self.conn.cursor()

    def setup(self):
        self.conn.commit()

    def check_menu(self, category):
        stmt = "SELECT name, price FROM food_details WHERE category IN (%s) ORDER BY ctid ASC;"
        args = (category,)
        self.cursor.execute(stmt, args)
        name_list = [x[0] for x in self.cursor.fetchall()]
        self.cursor.execute(stmt, args)
        price_list = [x[1] for x in self.cursor.fetchall()]
        return [name_list, price_list]

    def check_photo(self, category):
        stmt = "SELECT image FROM food_details WHERE category IN (%s) ORDER BY ctid ASC;"
        args = (category,)
        self.cursor.execute(stmt, args)
        return [x[0] for x in self.cursor.fetchall()]

    def edit_menu(self, name, image, price, category):
        stmt = "UPDATE food_details SET name = (%s), image = (%s), price = (%s) WHERE category IN (%s);"
        args = (name, image, price, category)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def time_list(self):
        stmt = "SELECT time_options FROM collection_time ORDER BY ctid ASC;"
        self.cursor.execute(stmt)
        return [[x[0]] for x in self.cursor.fetchall()]

    def add_time(self, collection_time, user_id):
        stmt = "UPDATE order_list SET collection_time = (%s) WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (collection_time, user_id)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_order(self, user_id, username, name, item_ordered):
        stmt = "INSERT INTO order_list (user_id, username, name, item_ordered, status) VALUES (%s, %s, %s, %s, 'PENDING');"
        args = (user_id, username, name, item_ordered)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def select_latest_item(self, user_id):
        stmt = "SELECT item_ordered FROM order_list WHERE user_id IN (%s) ORDER BY ctid DESC LIMIT 1;"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        return [x[0] for x in self.cursor.fetchall()]

    def select_latest_quantity(self, user_id):
        stmt = "SELECT quantity FROM order_list WHERE user_id IN (%s) ORDER BY ctid DESC LIMIT 1;"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        return [x[0] for x in self.cursor.fetchall()]

    def add_quantity(self, quantity, user_id, item_ordered):
        stmt = "UPDATE order_list SET quantity = (%s) WHERE user_id IN (%s) AND status = 'PENDING' AND item_ordered = (%s) AND ctid = (SELECT MAX(ctid) FROM order_list);"
        args = (quantity, user_id, item_ordered)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_location(self, location, user_id):
        stmt = "UPDATE order_list SET location = (%s) WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (location, user_id)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_remarks(self, remarks, user_id, item_ordered):
        stmt = "UPDATE order_list SET remarks = (%s) WHERE user_id IN (%s) AND status = 'PENDING' AND item_ordered = (%s) AND ctid = (SELECT MAX(ctid) FROM order_list);"
        args = (remarks, user_id, item_ordered)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def delete_order(self, user_id):
        stmt = "DELETE FROM order_list WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_full_name(self, full_name, user_id):
        stmt = "UPDATE order_list SET name = (%s) WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (full_name, user_id)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_contact_number(self, contact_number, user_id):
        stmt = "UPDATE order_list SET contact_number = (%s) WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (contact_number, user_id)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def add_receipt_image(self, receipt_image, user_id):
        stmt = "UPDATE order_list SET receipt_image = (%s) WHERE user_id IN (%s) AND status = 'PENDING';"
        args = (receipt_image, user_id)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def check_order(self, user_id):
        stmt = "SELECT item_ordered, quantity FROM order_list WHERE user_id IN (%s) AND status = 'PENDING' ORDER BY ctid ASC;"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        item_list = [x[0] for x in self.cursor.fetchall()]
        self.cursor.execute(stmt, args)
        quantity_list = [y[1] for y in self.cursor.fetchall()]
        price_list = []
        for i in item_list:
            next_stmt = "SELECT price FROM food_details WHERE name IN (%s);"
            next_args = (i,)
            self.cursor.execute(next_stmt, next_args)
            price_list.append(list(z[0] for z in
                                   self.cursor.fetchall()))
        flattened_list = [val for sublist in price_list for val in sublist]
        per_element_list = [a * b for a, b in zip(quantity_list,
                                                  flattened_list)]
        return [item_list, quantity_list, per_element_list]

    def check_offer(self):
        stmt = "SELECT offer FROM offer_table;"
        self.cursor.execute(stmt)
        return [x[0] for x in self.cursor.fetchall()]

    def paid_payment_status(self, user_id):
        stmt = "UPDATE order_list SET status = 'PAID' WHERE user_id IN (%s);"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def delete_paid_user(self, user_id):
        stmt = "DELETE FROM order_list WHERE user_id IN (%s) AND status = 'PAID';"
        args = (user_id,)
        self.cursor.execute(stmt, args)
        self.conn.commit()

    def retrieve_current_orders(self):
        stmt = "SELECT * FROM order_list WHERE status = 'PAID' ORDER BY collection_time ASC;"
        self.cursor.execute(stmt)
        return [x for x in self.cursor.fetchall()]

    def purge_order_list(self):
        stmt = "DELETE FROM order_list;"
        self.cursor.execute(stmt)
        self.conn.commit()
