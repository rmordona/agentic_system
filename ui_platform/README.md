1. Install PostgreSQL

% brew install postresql
✔︎ JSON API cask.jws.json                                                                                                                                                   Downloaded   15.3MB/ 15.3MB
✔︎ JSON API formula.jws.json                                                                                                                                                Downloaded   32.0MB/ 32.0MB
Warning: No available formula with the name "postresql". Did you mean postgresql@18, postgresql@17, postgresql@16, postgresql@15, postgresql@14, postgresql@13, postgresql@12 or postgrest?
==> Searching for similarly named formulae and casks...
==> Formulae
postgresql@18                                     postgresql@16                                     postgresql@14 (deprecated)                        postgresql@12 (deprecated)
postgresql@17                                     postgresql@15                                     postgresql@13 (deprecated)                        postgrest

To install postgresql@18, run:
  brew install postgresql@18

% brew install postgresql@18


2. Start PostgreSQL as service

% brew services start postgresql@18
==> Successfully started `postgresql@18` (label: homebrew.mxcl.postgresql@18)

3. Check status

% brew services list
Name          Status   User          File
kafka         none                   
podman        none                   
postgresql@18 error  1 raymondordona ~/Library/LaunchAgents/homebrew.mxcl.postgresql@18.plist
unbound       none                   

4. Stop Service

brew services stop postgresql@18

5. Set PATH for postgresql@18

echo 'export PATH="/usr/local/opt/postgresql@18/bin:$PATH"' >> ~/.zshrc

source ~/.zshrc

6. Initialize database

% mkdir -p /usr/local/lib/postgresql@18
% ln -s /usr/local/Cellar/postgresql@18/18.2/lib/postgresql/* /usr/local/lib/postgresql@18/
% /usr/local/opt/postgresql@18/bin/initdb -D /usr/local/var/postgresql@18
The files belonging to this database system will be owned by user "raymondordona".
This user must also own the server process.

The database cluster will be initialized with locale "en_US.UTF-8".
The default database encoding has accordingly been set to "UTF8".
The default text search configuration will be set to "english".

Data page checksums are enabled.

creating directory /usr/local/var/postgresql@18 ... ok
creating subdirectories ... ok
selecting dynamic shared memory implementation ... posix
selecting default "max_connections" ... 100
selecting default "shared_buffers" ... 128MB
selecting default time zone ... America/Los_Angeles
creating configuration files ... ok
running bootstrap script ... ok
performing post-bootstrap initialization ... ok
syncing data to disk ... ok

initdb: warning: enabling "trust" authentication for local connections
initdb: hint: You can change this by editing pg_hba.conf or using the option -A, or --auth-local and --auth-host, the next time you run initdb.

Success. You can now start the database server using:

    '/usr/local/opt/postgresql@18/bin/pg_ctl' -D '/usr/local/var/postgresql@18' -l logfile start

7. Run manually to see error details

% pg_ctl -D /usr/local/var/postgresql@18 start
waiting for server to start....2026-02-22 05:45:47.950 PST [46334] LOG:  starting PostgreSQL 18.2 (Homebrew) on x86_64-apple-darwin22.6.0, compiled by Apple clang version 14.0.3 (clang-1403.0.22.14.1), 64-bit
2026-02-22 05:45:47.951 PST [46334] LOG:  listening on IPv6 address "::1", port 5432
2026-02-22 05:45:47.951 PST [46334] LOG:  listening on IPv4 address "127.0.0.1", port 5432
2026-02-22 05:45:47.953 PST [46334] LOG:  listening on Unix socket "/tmp/.s.PGSQL.5432"
2026-02-22 05:45:47.956 PST [46340] LOG:  database system was shut down at 2026-02-22 05:43:30 PST
2026-02-22 05:45:47.959 PST [46334] LOG:  database system is ready to accept connections
 done
server started



8. Connect to postgresql

% psql -U postgres -d mydb 
2026-02-22 05:48:33.888 PST [46381] FATAL:  database "mydb" does not exist
psql: error: connection to server on socket "/tmp/.s.PGSQL.5432" failed: FATAL:  database "mydb" does not exist



############ for testing that postgres works, let's create a simple mydb and table called users

9. create mydb - for testing only

% createdb -U raymondordona mydb

10. Now connect:

% psql -U postgres -d mydb 
psql (18.2 (Homebrew))
Type "help" for help.

mydb=# 

OR

% psql -U raymondordona -d mydb 
psql (18.2 (Homebrew))
Type "help" for help.

mydb=# 



11. Create a table

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


12. Verify and inspect

mydb=# 
mydb=# CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE
mydb=# 
mydb=# 
mydb=# 
mydb=# \dt
             List of tables
 Schema | Name  | Type  |     Owner     
--------+-------+-------+---------------
 public | users | table | raymondordona
(1 row)

mydb=# \d users
                                           Table "public.users"
     Column      |            Type             | Collation | Nullable |              Default              
-----------------+-----------------------------+-----------+----------+-----------------------------------
 id              | integer                     |           | not null | nextval('users_id_seq'::regclass)
 username        | character varying(50)       |           | not null | 
 email           | character varying(255)      |           | not null | 
 hashed_password | text                        |           | not null | 
 created_at      | timestamp without time zone |           |          | CURRENT_TIMESTAMP
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)
    "users_username_key" UNIQUE CONSTRAINT, btree (username)


##################################### now for the actual context_platform platform

13. Create a new database

% psql -U raymondordona -d mydb     
psql (18.2 (Homebrew))
Type "help" for help.

mydb=# CREATE DATABASE context_platform;
CREATE DATABASE

14. Connect to the new database

% psql -U raymondordona -d context_platform

15. create table

context_platform=# \dt
Did not find any tables.
context_platform=# CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE
context_platform=# 
context_platform=# \dt
             List of tables
 Schema | Name  | Type  |     Owner     
--------+-------+-------+---------------
 public | users | table | raymondordona
(1 row)

context_platform=# 
context_platform=# \d users
                                           Table "public.users"
     Column      |            Type             | Collation | Nullable |              Default              
-----------------+-----------------------------+-----------+----------+-----------------------------------
 id              | integer                     |           | not null | nextval('users_id_seq'::regclass)
 username        | character varying(50)       |           | not null | 
 email           | character varying(255)      |           | not null | 
 hashed_password | text                        |           | not null | 
 created_at      | timestamp without time zone |           |          | CURRENT_TIMESTAMP
Indexes:
    "users_pkey" PRIMARY KEY, btree (id)
    "users_email_key" UNIQUE CONSTRAINT, btree (email)
    "users_username_key" UNIQUE CONSTRAINT, btree (username)

context_platform=# 


15. Creating a new user called johnsmith with welcome1 password on context_platform table with grants to users table:

% psql -d postgres
psql (18.2 (Homebrew))
Type "help" for help.

postgres=# CREATE ROLE johnsmith WITH LOGIN PASSWORD 'welcome1';
CREATE ROLE
postgres=# GRANT CONNECT ON DATABASE context_platform TO johnsmith;
GRANT
postgres=# \c context_platform
You are now connected to database "context_platform" as user "raymondordona".
context_platform=# GRANT USAGE ON SCHEMA public TO johnsmith;
GRANT
context_platform=# GRANT SELECT ON TABLE "users" TO johnsmith;
GRANT

16. test connecting using johnsmith

 % psql -U johnsmith -d context_platform -W
Password: 
psql (18.2 (Homebrew))
Type "help" for help.

context_platform=> 
context_platform=> \dt
             List of tables
 Schema | Name  | Type  |     Owner     
--------+-------+-------+---------------
 public | users | table | raymondordona
(1 row)

context_platform=> \d
                List of relations
 Schema |     Name     |   Type   |     Owner     
--------+--------------+----------+---------------
 public | users        | table    | raymondordona
 public | users_id_seq | sequence | raymondordona
(2 rows)



17. Now configure your backend (config.py) to use the database:

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://jonthsmith:welcome1@localhost:5432/context_platform")


18. For now, we have raymonordona as the superuser so we create the table over there.
    We can run this for jonthsmith but for now, nope!

-- 1. Connect to the right database as the admin
\c context_platform raymondordona

-- 2. Make johnsmith the owner of the schema so he has full control
ALTER SCHEMA public OWNER TO johnsmith;

-- 3. Just to be safe, make him the owner of the database too
ALTER DATABASE context_platform OWNER TO johnsmith;


19. Give full DML privileges to johnsmith:

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE users TO raymondordona;

GRANT USAGE, SELECT, UPDATE ON SEQUENCE users_id_seq TO johnsmith;
GRANT




20. Other tables:

-- -----------------------------
-- Table: users (assumes this exists)
-- -----------------------------
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE
);

-- -----------------------------
-- Table: threads
-- -----------------------------
CREATE TABLE IF NOT EXISTS threads (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(200) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Optional: trigger to auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_threads_updated_at
BEFORE UPDATE ON threads
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- -----------------------------
-- Table: chat_messages
-- -----------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    role VARCHAR(50) NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


21. More privileges

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE chat_messages to johnsmith;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE threads to johnsmith;

GRANT USAGE, SELECT ON SEQUENCE chat_messages_id_seq TO johnsmith;


##########################################

INSTALL PGVECTOR

for postgresql 16/17:
brew install pgvector

for postgresql 18:
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install


For our install, use this:
'/usr/local/Cellar/postgresql@18/18.3/bin/pg_ctl' -D '/usr/local/var/postgresql@18' -l logfile stop
'/usr/local/Cellar/postgresql@18/18.3/bin/pg_ctl' -D '/usr/local/var/postgresql@18' -l logfile start

Instead of this:
brew services restart postgresql


psql -U raymondordona -d context_platform


CREATE EXTENSION IF NOT EXISTS vector;



Create Tools table:

CREATE TABLE mcp_tools (
    tool_name TEXT PRIMARY KEY,
    description TEXT,
    embedding VECTOR(768)
);

Example select:

SELECT tool_name, description
FROM mcp_tools
ORDER BY embedding <-> :stage_embedding
LIMIT 5;

Create index

CREATE INDEX idx_tool_embedding
ON mcp_tools
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);


Example select:

SELECT tool_name, description
FROM mcp_tools
WHERE description ILIKE ANY(:intent_keywords)
ORDER BY embedding <-> :embedding
LIMIT 6;


# \d mcp_tools
                  Table "public.mcp_tools"
   Column    |     Type     | Collation | Nullable | Default 
-------------+--------------+-----------+----------+---------
 tool_name   | text         |           | not null | 
 description | text         |           |          | 
 embedding   | vector(1536) |           |          | 
Indexes:
    "mcp_tools_pkey" PRIMARY KEY, btree (tool_name)
    "idx_tool_embedding" ivfflat (embedding vector_cosine_ops) WITH (lists='100')


#### SUPERUSER PRIVILEGES ###

postgres=# \du
                               List of roles
   Role name   |                         Attributes                         
---------------+------------------------------------------------------------
 johnsmith     | 
 postgres      | Superuser
 raymondordona | Superuser, Create role, Create DB, Replication, Bypass RLS

postgres=# ALTER ROLE johnsmith WITH SUPERUSER;
ALTER ROLE
postgres=# \du
                               List of roles
   Role name   |                         Attributes                         
---------------+------------------------------------------------------------
 johnsmith     | Superuser
 postgres      | Superuser
 raymondordona | Superuser, Create role, Create DB, Replication, Bypass RLS

postgres=# \quit
pgvector % psql -U johnsmith -d context_platform -c "SHOW config_file;"
                 config_file                  
----------------------------------------------
 /usr/local/var/postgresql@18/postgresql.conf
(1 row)

