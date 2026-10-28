-- Local/lab runtime role. Do not reuse this password in production.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'orders_app'
    ) THEN
        CREATE ROLE orders_app LOGIN PASSWORD 'orders-app-dev';
    ELSE
        ALTER ROLE orders_app LOGIN PASSWORD 'orders-app-dev';
    END IF;
END
$$;

ALTER ROLE orders_app
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS;

GRANT CONNECT ON DATABASE orders TO orders_app;
GRANT USAGE ON SCHEMA public TO orders_app;
GRANT SELECT, INSERT ON TABLE public.orders TO orders_app;
GRANT USAGE, SELECT ON SEQUENCE public.orders_id_seq TO orders_app;
