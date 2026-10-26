ALTER TABLE cedar_press_subscribers
    ADD COLUMN display_name TEXT CHECK (length(display_name) <= 120);
