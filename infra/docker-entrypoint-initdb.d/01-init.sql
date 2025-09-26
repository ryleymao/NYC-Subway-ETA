DO $$
BEGIN
  PERFORM 1 FROM pg_database WHERE datname = 'nyc_subway';
  IF NOT FOUND THEN
    CREATE DATABASE nyc_subway;
  END IF;
END$$;
