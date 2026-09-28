\getenv langfuse_user LANGFUSE_DB_USER
\getenv langfuse_password LANGFUSE_DB_PASSWORD
\getenv langfuse_database LANGFUSE_DB_NAME

SELECT format(
	'CREATE ROLE %I LOGIN PASSWORD %L',
	:'langfuse_user',
	:'langfuse_password'
) \gexec

CREATE DATABASE :"langfuse_database" OWNER :"langfuse_user";

REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
REVOKE ALL ON DATABASE postgres FROM :"langfuse_user";
REVOKE CONNECT ON DATABASE :"langfuse_database" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"langfuse_database" TO :"langfuse_user";
