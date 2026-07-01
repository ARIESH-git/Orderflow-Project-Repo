# OrderFlow

[![CI Pipeline](https://github.com/ARIESH-git/Orderflow-Project-Repo/actions/workflows/ci.yaml/badge.svg)](https://github.com/ARIESH-git/Orderflow-Project-Repo/actions/workflows/ci.yaml)
![Kubernetes](https://img.shields.io/badge/Kubernetes-326CE5?style=flat&logo=kubernetes&logoColor=white)
![Kafka](https://img.shields.io/badge/Apache_Kafka-231F20?style=flat&logo=apache-kafka&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![Terraform](https://img.shields.io/badge/Terraform-7B42BC?style=flat&logo=terraform&logoColor=white)
![ArgoCD](https://img.shields.io/badge/ArgoCD-EF7B4D?style=flat&logo=argo&logoColor=white)
![AWS](https://img.shields.io/badge/AWS-232F3E?style=flat&logo=amazon-aws&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-F46800?style=flat&logo=grafana&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)

An event-driven order processing platform I built on Kubernetes to prove I can reason about distributed systems — not just deploy a CRUD app and call it a project.

---

## Demo

[![OrderFlow Demo](https://img.youtube.com/vi/W64OjGid2R8/maxresdefault.jpg)](https://youtu.be/W64OjGid2R8)

> Click to watch — canary rollback, pod self-healing, and AI copilot diagnosing an incident and posting to Slack in real time.

---
## Screenshots

**Grafana Dashboard**
![Grafana Dashboard](docs/images/grafana%20dashboard.png)

**GitHub Actions CI Pipeline**
![CI Pipeline](docs/images/github%20actions%20CICD.png)

**ArgoCD GitOps**
![ArgoCD](docs/images/argocd%20page.png)

**Terraform Apply**
![Terraform](docs/images/terraform%20complete%20resource%20creation.png)

**KEDA Autoscaling**
![KEDA](docs/images/keda%20proof.png)

**Order Placed**
![Order](docs/images/order%20placed.png)

## Why I built this

I wanted one project that covers the full stack a DevOps/Cloud engineer actually touches. Not just a Dockerfile and a GitHub Actions workflow. Something with real failure modes — what happens when Kafka lag spikes, when a bad deploy ships, when a consumer crashes. Those are the problems that matter in a real job, and I wanted to be able to walk through all of them in an interview.

---

## What it does

Client places an order → FastAPI writes it to DynamoDB and publishes an event to Kafka → two independent consumers pick it up (inventory update, notification) → KEDA scales the consumers up and down based on actual Kafka consumer lag → everything deploys through ArgoCD from Git → if something breaks, a LangChain agent reads the logs, checks past incidents, and posts a diagnosis to Slack before anyone even opens their laptop.

---

## Architecture

```
Client
  │
  ▼
FastAPI (JWT + GitHub OAuth2)
  │
  ├──► DynamoDB (order storage)
  │
  └──► Kafka (order-placed topic, 8 partitions)
            │
            ├──► Inventory Consumer  ◄── KEDA (scales on Kafka lag)
            │         └──► DynamoDB + Redis
            │
            └──► Notification Consumer  ◄── KEDA (scales on Kafka lag)

Prometheus + Loki + Grafana  ◄── scrapes all services
        │
   Alertmanager
        │
        ▼
LangChain Agent (Groq LLM)
  ├── Tool 1: Query Loki for recent errors
  ├── Tool 2: RAG lookup over past incident notes
  └── Tool 3: Post diagnosis to Slack

ArgoCD             ◄── watches this repo, auto-syncs on every push
Argo Rollouts      ◄── canary deployments with Prometheus-backed analysis
GitHub Actions     ◄── lint → SAST → build → Trivy → ECR push via OIDC
Terraform          ◄── VPC, EKS, ECR, IAM OIDC role on AWS
```

---

## Stack decisions

**Kafka over RabbitMQ or SQS** — needed two independent consumer groups reading the same stream, plus replay for incident analysis. RabbitMQ deletes on ack. SQS is AWS-only with best-effort ordering.

**KEDA over HPA** — my consumers aren't CPU-bound, they're waiting on messages. KEDA scales on consumer lag, which is the actual signal that matters.

**ArgoCD over manual kubectl** — every change is a Git commit. Drift is auto-corrected. Nothing ships outside of Git.

**Argo Rollouts over blue-green** — the API is customer-facing. Gradual traffic shift with live Prometheus error-rate analysis means a bad deploy gets caught before it reaches everyone.

**Terraform for cloud infra** — I wanted to prove I can provision the cluster itself, not just deploy things onto one someone else created. VPC, EKS, ECR, IAM OIDC — all through `terraform apply`.

**LangChain agent with 3 tools** — kept it small enough that I can explain every line in an interview. It works, and I built it myself.

**DynamoDB over Postgres** — simple key-based access pattern, no relational joins needed. Haven't gone deep enough on Postgres yet to defend it honestly in an interview, so I didn't fake it.

---

## CI/CD Pipeline

Every push to master runs:

```
flake8 lint
  └── Bandit SAST (fails on High severity findings)
        └── Docker build
              └── Trivy image scan (fails on CRITICAL CVEs)
                    └── Push to ECR via GitHub OIDC
                              no AWS credentials stored anywhere
```

---

## Chaos tested

| What I broke | What happened |
|---|---|
| 200 concurrent orders | KEDA scaled consumers from 1 to 8 pods on Kafka lag |
| Pushed a build with 50% random 500s | Argo Rollouts detected error rate spike, aborted canary before full traffic shift |
| Killed a consumer pod | Kubernetes restarted it automatically; AI copilot posted diagnosis to Slack in ~12 seconds |

---

## Run it locally

```bash
git clone https://github.com/ARIESH-git/Orderflow-Project-Repo.git
cd Orderflow-Project-Repo
docker-compose up
```

Get a token and place an order:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your-user","password":"your-password"}'

curl -X POST "http://localhost:8000/orders?item=sneakers&quantity=2" \
  -H "Authorization: Bearer <token>"
```

---

## Deploy to Kubernetes

```bash
kind create cluster --name akcluster
helm upgrade orderflow helm/orderflow --install
```

Access Grafana:

```bash
kubectl port-forward -n monitoring svc/grafana 3000:80
# http://localhost:3000  (admin / orderflow123)
```

---

## What I'd improve next

- Distributed tracing with Tempo and OpenTelemetry — right now I can see metrics and logs but I can't follow a single order across all services in one trace
- Give the AI agent actual remediation actions, not just diagnosis
- PostgreSQL for order history reporting once I've gone deep enough to defend it

---

## Contact

- GitHub: [ARIESH-git](https://github.com/ARIESH-git)
- LinkedIn: [www.linkedin.com/in/ariesh-k-19b261394]
- Email: ariesharun07@gmail.com
