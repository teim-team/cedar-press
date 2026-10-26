-- Stripe now collects the buyer's email. Existing purchases and account links remain intact.
ALTER TABLE cedar_press_guest_checkouts ALTER COLUMN email DROP NOT NULL;
DROP INDEX cedar_press_guest_email_pending;
CREATE INDEX cedar_press_guest_email ON cedar_press_guest_checkouts(email);
ALTER TABLE cedar_press_subscriptions ADD COLUMN customer_id TEXT;
UPDATE cedar_press_subscriptions s SET customer_id=u.stripe_customer_id
FROM cedar_press_subscribers u WHERE u.id=s.user_id;
