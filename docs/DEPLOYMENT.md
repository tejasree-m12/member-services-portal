# Deploying to AWS (EC2 + S3)

This guide deploys the project using services in the AWS free tier.

- **Frontend:** static files in an S3 bucket with static website hosting.
- **Backend:** one Ubuntu EC2 instance running nginx, gunicorn and MySQL.
- **Documents:** a second, private S3 bucket, reached through an IAM role.

> **Before you start.** AWS resources can cost money once free-tier limits are passed. Set a billing alarm, and delete everything when you are done (see the last section). The setup below is HTTP only and suitable for a demo with synthetic data. Do not put real personal data on it.

## 1. Create the S3 buckets

Bucket names are global, so pick unique ones. The examples use `my-portal-frontend` and `my-portal-documents`.

**Documents bucket (private)**
1. S3 console, **Create bucket**, name `my-portal-documents`, keep **Block all public access** on.
2. Keep default encryption on.

**Frontend bucket (public website)**
1. **Create bucket**, name `my-portal-frontend`, turn **Block all public access** off and confirm.
2. **Properties**, **Static website hosting**, **Enable**. Index document: `index.html`. Error document: `index.html`.
   The error document matters: the React app handles its own URLs, so a request for `/claims/17` must still return `index.html`.
3. **Permissions**, **Bucket policy**:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicRead",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::my-portal-frontend/*"
    }
  ]
}
```

Note the **website endpoint** shown under static website hosting, e.g. `http://my-portal-frontend.s3-website-us-east-1.amazonaws.com`.

## 2. Create an IAM role for the EC2 instance

The server needs to read and write the documents bucket. Give it a role, not access keys.

1. IAM, **Roles**, **Create role**, trusted entity **AWS service**, use case **EC2**.
2. Skip the managed policies, name the role `member-portal-ec2`, create it.
3. Open the role, **Add permissions**, **Create inline policy**, JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
      "Resource": "arn:aws:s3:::my-portal-documents/*"
    }
  ]
}
```

This is "least privilege": three actions on one bucket, nothing else.

## 3. Launch the EC2 instance

1. EC2, **Launch instance**. AMI: Ubuntu Server 24.04 LTS. Type: `t2.micro` or `t3.micro` (free tier).
2. Create or choose a **key pair** and download the `.pem` file. Keep it private.
3. **Security group** inbound rules:
   - SSH (22) from **My IP** only.
   - HTTP (80) from anywhere.
   - Do **not** open 3306 (MySQL) or 8000 (gunicorn). They are reached only from inside the instance.
4. **Advanced details**, **IAM instance profile**: `member-portal-ec2`.
5. Launch, then note the **public IPv4 address**.

Connect:

```bash
chmod 400 my-key.pem
ssh -i my-key.pem ubuntu@<EC2_PUBLIC_IP>
```

## 4. Set up the server

On the instance:

```bash
curl -fsSL https://raw.githubusercontent.com/<your-user>/<your-repo>/main/deploy/ec2_setup.sh -o ec2_setup.sh
bash ec2_setup.sh https://github.com/<your-user>/<your-repo>.git
```

The script installs Python, nginx and MySQL, clones the repository to `/opt/member-portal`, creates a virtual environment, and installs the nginx site and the systemd service. Read it before running it; it is short.

## 5. Create the database

```bash
sudo mysql
```

```sql
CREATE DATABASE member_portal CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'portal'@'localhost' IDENTIFIED BY 'choose-a-strong-password';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, REFERENCES ON member_portal.* TO 'portal'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

The application user gets only the privileges it needs on its own database. It is not root.

## 6. Configure and start the API

Generate two secrets:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Create `/opt/member-portal/backend/.env`:

```ini
SECRET_KEY=<first secret>
JWT_SECRET_KEY=<second secret>
DATABASE_URL=mysql+pymysql://portal:choose-a-strong-password@127.0.0.1:3306/member_portal?charset=utf8mb4
CORS_ORIGINS=http://my-portal-frontend.s3-website-us-east-1.amazonaws.com
S3_BUCKET=my-portal-documents
AWS_REGION=us-east-1
```

`CORS_ORIGINS` must be the frontend's website endpoint exactly, with no trailing slash.

```bash
sudo chown ubuntu:portal /opt/member-portal/backend/.env
sudo chmod 640 /opt/member-portal/backend/.env

cd /opt/member-portal/backend                  # the flask command reads .env from this folder
../venv/bin/flask --app wsgi init-db
../venv/bin/flask --app wsgi create-admin      # or: ../venv/bin/flask --app wsgi seed   (demo data)

sudo systemctl start member-portal
curl http://127.0.0.1/api/v1/health            # {"database":"ok","status":"ok"}
```

From your own computer, `http://<EC2_PUBLIC_IP>/api/v1/health` should return the same.

## 7. Build and upload the frontend

On your own computer (needs the AWS CLI configured with `aws configure`):

```bash
cd frontend
VITE_API_BASE_URL=http://<EC2_PUBLIC_IP>/api/v1 npm run build
aws s3 sync dist s3://my-portal-frontend --delete
```

On Windows PowerShell, set the variable first: `$env:VITE_API_BASE_URL="http://<EC2_PUBLIC_IP>/api/v1"; npm run build`.

Open the S3 website endpoint in a browser and sign in.

## 8. Deploying from GitHub Actions

`.github/workflows/deploy.yml` automates steps 7 and the backend update. In the GitHub repository, **Settings**, **Secrets and variables**, **Actions**:

| Kind | Name | Value |
|---|---|---|
| Secret | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | Keys of an IAM user allowed only `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket` on the frontend bucket |
| Secret | `EC2_HOST` | The instance's public IP or DNS name |
| Secret | `EC2_USER` | `ubuntu` |
| Secret | `EC2_SSH_KEY` | The full contents of the `.pem` file |
| Variable | `AWS_REGION` | e.g. `us-east-1` |
| Variable | `FRONTEND_BUCKET` | `my-portal-frontend` |
| Variable | `VITE_API_BASE_URL` | `http://<EC2_PUBLIC_IP>/api/v1` |

The GitHub-hosted runner must be able to reach port 22, so the security group's SSH rule would need to allow it. Runner IP addresses change, which is one reason larger teams deploy with AWS Systems Manager or CodeDeploy instead of SSH.

Then: **Actions**, **Deploy**, **Run workflow**. The workflow runs the full CI checks, uploads the frontend, and runs `deploy/deploy_backend.sh` on the server. That script checks out the new commit, installs dependencies, restarts gunicorn, waits for the health check, and rolls back to the previous commit if the check fails.

## 9. Operating it

| Task | Command (on the instance) |
|---|---|
| Is the service running? | `systemctl status member-portal` |
| Application logs, live | `journalctl -u member-portal -f` |
| Last 100 log lines | `journalctl -u member-portal -n 100 --no-pager` |
| nginx access / error logs | `sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log` |
| Restart | `sudo systemctl restart member-portal` |
| Back up the database | `mysqldump -u portal -p member_portal > backup_$(date +%F).sql` |

**Typical problems**

| Symptom | Likely cause |
|---|---|
| Browser console: "blocked by CORS policy" | `CORS_ORIGINS` does not match the frontend URL exactly. Fix `.env`, restart. |
| `502 Bad Gateway` from nginx | gunicorn is not running. Check `journalctl -u member-portal`. |
| `503` from `/health` | The API is up but cannot reach MySQL. Check `DATABASE_URL` and `systemctl status mysql`. |
| Upload fails with a 500, log shows `AccessDenied` | The instance has no IAM role, or the role's policy names a different bucket. |
| Refreshing a page on S3 gives 404 | The bucket's error document is not set to `index.html`. |

## 10. Clean up

To stop all charges: terminate the EC2 instance, empty and delete both buckets, delete the IAM role, the IAM user and its keys, and the key pair.
