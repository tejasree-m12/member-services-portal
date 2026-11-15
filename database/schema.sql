-- Member Services Portal: MySQL schema (reference copy).
-- Generated from the SQLAlchemy models with:  flask --app wsgi print-schema
-- The application creates these tables itself with:  flask --app wsgi init-db

CREATE TABLE providers (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	npi VARCHAR(10) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	specialty VARCHAR(100) NOT NULL, 
	city VARCHAR(100) NOT NULL, 
	state VARCHAR(2) NOT NULL, 
	phone VARCHAR(20), 
	accepting_patients BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (npi)
);

CREATE INDEX ix_providers_name ON providers (name);

CREATE INDEX ix_providers_specialty ON providers (specialty);

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	email VARCHAR(255) NOT NULL, 
	full_name VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	is_active BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);

CREATE TABLE audit_logs (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER, 
	action VARCHAR(50) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id INTEGER, 
	details TEXT, 
	ip_address VARCHAR(45), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_logs_action ON audit_logs (action);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

CREATE TABLE members (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	member_number VARCHAR(20) NOT NULL, 
	first_name VARCHAR(80) NOT NULL, 
	last_name VARCHAR(80) NOT NULL, 
	date_of_birth DATE NOT NULL, 
	email VARCHAR(255), 
	phone VARCHAR(20), 
	plan_type VARCHAR(30) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	primary_provider_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (member_number), 
	FOREIGN KEY(primary_provider_id) REFERENCES providers (id)
);

CREATE INDEX ix_members_last_name ON members (last_name);

CREATE INDEX ix_members_plan_type ON members (plan_type);

CREATE INDEX ix_members_status ON members (status);

CREATE TABLE claims (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	claim_number VARCHAR(20) NOT NULL, 
	member_id INTEGER NOT NULL, 
	provider_id INTEGER NOT NULL, 
	service_date DATE NOT NULL, 
	procedure_code VARCHAR(5) NOT NULL, 
	diagnosis_code VARCHAR(8) NOT NULL, 
	billed_amount NUMERIC(10, 2) NOT NULL, 
	approved_amount NUMERIC(10, 2), 
	status VARCHAR(20) NOT NULL, 
	denial_reason VARCHAR(255), 
	created_by_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (claim_number), 
	FOREIGN KEY(member_id) REFERENCES members (id), 
	FOREIGN KEY(provider_id) REFERENCES providers (id), 
	FOREIGN KEY(created_by_id) REFERENCES users (id)
);

CREATE INDEX ix_claims_member_id ON claims (member_id);

CREATE INDEX ix_claims_provider_id ON claims (provider_id);

CREATE INDEX ix_claims_status_created ON claims (status, created_at);

CREATE TABLE claim_documents (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	claim_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_key VARCHAR(500) NOT NULL, 
	content_type VARCHAR(100) NOT NULL, 
	size_bytes INTEGER NOT NULL, 
	uploaded_by_id INTEGER, 
	uploaded_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(claim_id) REFERENCES claims (id), 
	FOREIGN KEY(uploaded_by_id) REFERENCES users (id)
);

CREATE INDEX ix_claim_documents_claim_id ON claim_documents (claim_id);

CREATE TABLE claim_status_history (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	claim_id INTEGER NOT NULL, 
	from_status VARCHAR(20), 
	to_status VARCHAR(20) NOT NULL, 
	note VARCHAR(500), 
	changed_by_id INTEGER, 
	changed_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(claim_id) REFERENCES claims (id), 
	FOREIGN KEY(changed_by_id) REFERENCES users (id)
);

CREATE INDEX ix_claim_status_history_claim_id ON claim_status_history (claim_id);

