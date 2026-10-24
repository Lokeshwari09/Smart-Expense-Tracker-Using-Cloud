# Smart Expense Tracker Using Cloud

A cloud-ready personal finance app. Users add expenses, the app **auto-categorises** them, tracks a
**monthly budget**, **forecasts** month-end spending, and shows charts. It runs in **Docker**,
deploys to an **AWS EC2** VM (with optional **S3** backups), can be hosted in an **Oracle VirtualBox**
VM, and its cloud behaviour is analysed with a **CloudSim** simulation.

## 1. Project structure

```
smart-expense-tracker/
├── app.py                      Flask backend + REST API + SQLite
├── templates/index.html        Dashboard page
├── static/style.css, app.js    Styling, charts (Chart.js), API calls
├── requirements.txt
├── Dockerfile, docker-compose.yml, .dockerignore
├── tests/test_app.py           Automated tests (pytest)
├── cloudsim/
│   ├── cloud_simulation.py     Python CloudSim-style simulation (runs directly in VS Code)
│   └── ExpenseTrackerSimulation.java   Real CloudSim 3.0.3 program
├── aws/ec2_setup.sh            One-shot EC2 / VM setup script
├── aws/s3_backup_policy.json   IAM policy for S3 backups
└── .vscode/launch.json         F5 run configs
```

## 2. Run directly in VS Code (no Docker needed)

1. Install Python 3.10+ and open this folder in VS Code (`File > Open Folder`).
2. Open a terminal (`Ctrl + ``) and run:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows   (Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py
```

3. Open **http://localhost:5000**. Press `F5` and choose "Run Expense Tracker" to debug instead.
4. Run the tests: `pytest -q`

The database is created automatically at `data/expenses.db`.

## 3. Run with Docker

```bash
docker compose up --build
```

Open http://localhost:5000. Data is kept in the `expense-data` Docker volume.
Stop with `docker compose down`.

## 4. Deploy on AWS Console (EC2 + S3)

**A. Launch the server**
1. AWS Console > **EC2 > Launch instance**. Name: `expense-tracker`. AMI: *Ubuntu 22.04* (free tier). Type: `t2.micro`/`t3.micro`.
2. Create or choose a key pair. Under **Network settings > Security group** allow: SSH (22) from *My IP*, **Custom TCP 5000** from anywhere.
3. Launch, then connect (EC2 Instance Connect or `ssh -i key.pem ubuntu@<public-ip>`).

**B. Install and run**
```bash
git clone <your-repo-url> smart-expense-tracker     # or upload with scp / WinSCP
cd smart-expense-tracker
bash aws/ec2_setup.sh
```
Open `http://<EC2-public-ip>:5000`.

**C. Enable S3 backup (optional)**
1. **S3 > Create bucket** (e.g. `expense-tracker-backup-yourname`).
2. **IAM > Policies > Create policy > JSON**: paste `aws/s3_backup_policy.json` (replace `YOUR-BUCKET-NAME`). Create a role for **EC2**, attach the policy, then **EC2 > Actions > Security > Modify IAM role** and attach it.
3. In `docker-compose.yml` uncomment `S3_BUCKET` and `AWS_DEFAULT_REGION`, then `docker compose up -d --build`.
4. Click **Backup to AWS S3** on the dashboard; the file appears under `backups/` in the bucket.

**D. Scaling (for the report)**: create an AMI of the instance, a Launch Template, an **Auto Scaling Group** (min 1, max 3, CPU target 50%) behind an **Application Load Balancer** with health check path `/health`.

## 5. Run on Oracle VirtualBox

1. Create a VM in VirtualBox: Ubuntu Server ISO, 2 GB RAM, 2 CPUs, 20 GB disk.
2. **Settings > Network > Adapter 1 > NAT > Advanced > Port Forwarding**: Host port `5000` > Guest port `5000`.
3. Inside the VM: `bash aws/ec2_setup.sh` (installs Docker and starts the app).
4. On your host browser open **http://localhost:5000**.

## 6. CloudSim simulation

**Easy (Python, runs in VS Code):**
```bash
python cloudsim/cloud_simulation.py
```
Compares a fixed 1-VM deployment against an auto-scaled one under a month-end traffic spike and
prints response time, VM utilisation and cost.

**Java CloudSim 3.0.3:** install the *Extension Pack for Java*, download `cloudsim-3.0.3.jar` and
`commons-math3`, add them under *Java Projects > Referenced Libraries*, then run
`cloudsim/ExpenseTrackerSimulation.java` (package `expense`). It simulates 1 datacenter, 2 hosts,
4 VMs and 20 request cloudlets.

## 7. REST API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Health check (load balancer) |
| GET / POST | `/api/expenses` | List / add expense (`description`, `amount`, optional `category`, `spent_on`) |
| DELETE | `/api/expenses/<id>` | Delete expense |
| GET | `/api/summary?month=YYYY-MM` | Totals, categories, forecast, budget alert |
| POST | `/api/budget` | Set monthly budget (`{"budget": 25000}`) |
| GET | `/api/export.csv` | Download all expenses |
| POST | `/api/backup` | Back up database to S3 |

## 8. Architecture (for your report)

```
Browser ──HTTP──> [AWS EC2 / VirtualBox VM]
                   └─ Docker container: Flask (gunicorn) + SQLite volume
                          └─ boto3 ──> Amazon S3 (backups)
Load balancing / Auto Scaling: ALB + ASG, health check /health
Performance analysis: CloudSim simulation
```

Cloud concepts covered: IaaS (EC2/VirtualBox), containers (Docker), object storage (S3), IAM roles,
load balancing, auto scaling, virtualization and simulation (CloudSim).
