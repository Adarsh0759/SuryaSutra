# SuryaSutra — cloud, containers & CI/CD, explained

This is the companion to `docs/NLP_CONCEPTS.md`. That one explains what the app *does*;
this one explains how it actually **runs**, how it gets from your laptop to a public
URL, and what each infrastructure piece is for. Same rule as CLAUDE.md's teaching
mandate: concept → why → alternative → what we actually built, grounded in real file
paths and the real problems we hit (not hypothetical ones).

**Important scope note**: none of this infrastructure is part of the research/product
work CLAUDE.md actually scopes for the prototype (§15/§16 only call for a local
`docker compose up`). This was built as a separate, explicit ask — a public demo link
plus hands-on AWS/Jenkins practice (`docs/DECISIONS.md`, D-43). Good to know so you
don't confuse "what the grader/investor needs to see" with "what this project's
research milestones require."

---

## 1. Why any of this is needed at all

Your laptop running `docker compose up` works great for you, but nobody else can reach
`localhost:5173`. To give someone else a clickable link, the app has to run on a
machine that's (a) always on and (b) has a public IP address. That's what "the cloud"
is, mechanically — a company (AWS here) rents you a computer that lives in their data
center instead of your house, with a public IP already attached.

---

## 2. Docker — packaging the app so it runs the same everywhere

### 2a. The concept

**Problem it solves**: "works on my machine" — your laptop has a specific Python
version, specific installed libraries, a specific OS. A server almost certainly
doesn't match that exactly. A **container** packages an application *and* everything it
needs to run (exact Python version, exact library versions, OS-level dependencies)
into one unit that runs identically on your laptop, a teammate's laptop, or a cloud
server.

**Container vs. virtual machine (the alternative)**: a VM virtualizes an entire
computer, including its own OS kernel — heavy (gigabytes, minutes to boot). A container
shares the host machine's kernel and only packages the application layer — light
(megabytes to low-gigabytes, seconds to start). Containers are the right tool here
because SuryaSutra doesn't need OS-level isolation, just dependency isolation.

### 2b. Image vs. container

An **image** is the packaged, built artifact (a stopped, "frozen" template — built once
from a `Dockerfile`). A **container** is a *running instance* of an image — you can
start multiple containers from the same image. Analogy: image = class, container =
object.

### 2c. The actual Dockerfiles

**`Dockerfile.backend`** — builds the FastAPI/Python backend:
```dockerfile
FROM python:3.11-slim                       # base image: minimal Debian + Python 3.11
RUN apt-get install -y build-essential      # needed to build some Python packages' C extensions
RUN pip install torch --index-url .../cpu   # CPU-only PyTorch — see §6a, the incident this fixed
RUN pip install -e .                        # editable install — see §6b, the incident this caused/fixed
CMD ["uvicorn", "suryasutra.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
Each `RUN`/`COPY` line adds a new, cached **layer** — if you change one line, Docker
only rebuilds that layer and everything after it, not the whole image from scratch.
That's why dependency-install steps are placed before copying application code: code
changes a lot, dependencies don't, so this ordering maximizes cache reuse.

**`Dockerfile.frontend`** — a **multi-stage build**: stage 1 (`node:20-slim`) runs
`npm run build` to produce static HTML/JS/CSS; stage 2 (`nginx:1.27-alpine`) copies
*only* those built static files in and serves them. The first stage's ~1GB of
`node_modules` never ends up in the final, shipped image — only the output does.

### 2d. docker-compose — running multiple containers together

**Problem it solves**: SuryaSutra isn't one container, it's two (`backend`, `frontend`)
that need to talk to each other, plus shared volumes and environment config. Starting
each with a long hand-typed `docker run ...` command is error-prone and not
reproducible. `docker-compose.yml` declares the whole stack — which images to build,
what ports to expose, what volumes to mount, what depends on what — in one file, and
`docker compose up` brings all of it up together.

- **Volumes** (`docker-compose.yml`): a way to persist data *outside* a container's own
  filesystem, so it survives a container being deleted/recreated. SuryaSutra mounts
  `./data/raw` and `./data/processed` from the host, and a named volume
  `huggingface-cache` for the downloaded embedding model — without that last one,
  every fresh container would re-download ~130MB from Hugging Face Hub every time.
- **Networking**: compose automatically puts both containers on one private network
  and lets them reach each other by service name — the frontend's nginx config
  (`web/nginx.conf`) proxies `/api/*` to `http://backend:8000/`, where `backend` is
  just the service name from `docker-compose.yml`, not an IP address.
- **`docker-compose.prod.yml`**: an *override* file, layered on top of the base with
  `docker compose -f docker-compose.yml -f docker-compose.prod.yml up`, that changes
  only the frontend's port mapping (`80:80` instead of `5173:80`) for the deploy
  server — the base file stays exactly what you run locally.

---

## 3. AWS / EC2 — renting the actual computer

### 3a. EC2, in one sentence

EC2 (Elastic Compute Cloud) rents you a virtual machine ("instance") in AWS's data
centers, billed by the hour (or free, within limits, on the "free tier").

### 3b. Region

AWS has data centers all over the world, grouped into **regions** (e.g. `us-east-1` =
Northern Virginia). Everything you create — instances, security groups — lives in one
region. SuryaSutra's instances are in `us-east-1`; this mostly just affects latency and
nothing else for a demo of this size.

### 3c. Instance type

`t3.micro` names the instance's hardware spec — here, 2 vCPUs (burstable, not
dedicated) and **1GB of RAM**. This is the smallest size eligible for AWS's free tier
(750 hours/month for 12 months on a new account). 1GB is tight for building a
Python ML-dependency-heavy Docker image — this constraint directly shaped two real
design decisions (§6a and §6c).

### 3d. VPC and subnets

A **VPC** (Virtual Private Cloud) is your own private, isolated slice of AWS's
network — every resource you create lives inside one. A VPC is divided into
**subnets**, each tied to one physical availability zone. Every new AWS account gets a
"default VPC" with one subnet per zone already set up (what SuryaSutra's two instances
both launch into) — you only need to build a custom VPC when you need more control than
that (e.g. fully private subnets with no internet access), which wasn't needed here.

### 3e. Security groups — the firewall

**Concept**: a security group is a virtual firewall attached to an instance, controlling
what network traffic is allowed in (and out). By default, *everything inbound is
denied* unless a rule explicitly allows it — "deny by default" is the safe starting
point.

**What SuryaSutra actually has**:

- `suryasutra-app-sg`: allows port 22 (SSH) only from the founder's own IP, port 80
  (the app itself) from anywhere (`0.0.0.0/0` — that's the point, it's the public demo),
  and — added later — port 22 from `suryasutra-jenkins-sg` specifically (see below).
- `suryasutra-jenkins-sg`: allows port 22 and 8080 (the Jenkins web UI) only from the
  founder's own IP — nothing about Jenkins is meant to be public.

**A rule can reference another security group as its source**, instead of a fixed IP
range — "allow traffic from any instance that's a member of `suryasutra-jenkins-sg`,"
rather than hardcoding an IP that could change. This is the mechanism behind the real
incident in §6d.

### 3f. Public IP vs. private IP

Every instance in a VPC gets a **private IP** (e.g. `172.31.15.233`) — only reachable
from other instances inside the same VPC, never from the public internet — and,
optionally, a **public IP** (e.g. `100.61.126.234`) via AWS's **Internet Gateway**,
reachable from anywhere. Traffic between two instances *in the same VPC* should
normally go over the private IP: it's faster (no internet round-trip), free (no data
transfer charges), and — critically, as §6d explains — it's the only way
security-group-source rules actually work.

### 3g. Key pairs — SSH authentication

AWS instances don't use passwords for SSH login by default — they use a **key pair**:
AWS holds the *public* key, baked into the instance at launch; you hold the matching
*private* key, generated once and shown to you exactly once. Whoever has the private
key file can SSH in; nobody else can. SuryaSutra's key
(`suryasutra-deploy-key`) was generated via `aws ec2 create-key-pair`, with its output
piped straight to a local file — the key's actual bytes were never typed into, or
displayed within, this conversation.

---

## 4. Jenkins — continuous integration / continuous deployment (CI/CD)

### 4a. The concept

**Problem it solves**: without automation, "deploying" means manually SSHing in,
pulling the latest code, and rebuilding, every single time — slow, and easy to forget a
step. CI/CD means: a tool watches your Git repository, and on a new commit, it
automatically runs a defined sequence of steps (build, test, deploy) — the same steps,
every time, without a human doing it by hand.

**Jenkins** is a widely-used, open-source, self-hosted CI/CD server. The alternative
would be a hosted service like GitHub Actions — SuryaSutra uses Jenkins specifically
because that was the explicit ask (hands-on Jenkins experience), not because it's
uniquely suited to this project.

### 4b. How Jenkins is actually running here

Jenkins itself runs **inside a Docker container**, on its own dedicated EC2 instance
(`suryasutra-jenkins`) — started via `docker run jenkins/jenkins:lts` in
`infra/jenkins-userdata.sh`. That script also sets up a 2GB swap file, since 1GB of
real RAM is tight for Jenkins plus any build tooling.

### 4c. Pipeline and Jenkinsfile

A Jenkins **pipeline** is a defined sequence of stages. Instead of configuring it by
hand through the web UI, it's written as code — a `Jenkinsfile`, committed to the repo
itself (so the deploy process is version-controlled, same as the application code):

```groovy
pipeline {
    stages {
        stage('Checkout') { steps { checkout scm } }      // pull the latest code
        stage('Deploy to app server') {
            steps {
                sshagent(credentials: ['suryasutra-deploy-key']) {
                    sh "ssh ec2-user@${APP_HOST} ' ... docker compose up -d --build ... '"
                }
            }
        }
        stage('Smoke test') {
            steps { sh "curl -sf http://${APP_HOST}/api/health" }   // did it actually come up?
        }
    }
}
```

**Key design decision**: Jenkins does **not** build the (large, ML-dependency-heavy)
backend image on its own 1GB instance. Instead, the pipeline SSHes into the *app*
instance and runs the build *there* — so the Jenkins box only ever needs git and an SSH
client, never Docker or gigabytes of Python ML packages. This is exactly the kind of
tradeoff real CI/CD setups make constantly: where does the actual work happen, versus
where does the orchestration happen.

### 4d. Credentials

Jenkins has its own encrypted **credential store** — secrets (like the SSH private key)
are uploaded to it once and referenced by an id (`suryasutra-deploy-key`) from the
pipeline, never hardcoded into the `Jenkinsfile` itself. The key was loaded in by
having Jenkins' own script console read it from a temporary file *on its own disk*
(staged there via `scp`, then deleted right after) — so the key's contents never
appeared in a chat transcript or a shell command's visible output.

### 4e. What triggers a build: polling vs. webhooks

The standard, fast way for GitHub to tell Jenkins "a new commit landed" is a
**webhook** — GitHub sends an HTTP request to Jenkins the moment you push. That requires
Jenkins to be reachable *from GitHub's servers*, i.e. publicly accessible — which
directly conflicts with locking Jenkins' UI down to one IP (§3e). The alternative,
used here: **SCM polling** — Jenkins itself checks GitHub every 5 minutes
(`H/5 * * * *`, the pipeline's trigger) and starts a build if anything changed. Slower
(up to a 5-minute delay) but needs zero public inbound access to Jenkins — the right
tradeoff for a small, security-conscious demo setup.

---

## 5. Git — tying it all together

Git itself isn't new to you, but its role here is worth naming explicitly: it's the
single source of truth both Jenkins and the app server pull from. `git push` to
`main` is the *only* action that starts the whole chain: Jenkins polls → sees a new
commit → checks it out → SSHes to the app server → the app server does its own
`git fetch && git reset --hard origin/main` → rebuilds → restarts. Nothing is ever
copied by hand between environments; the repository is the only path code takes to
reach the running app.

---

## 6. Four real incidents, and what each one teaches

Abstract cloud concepts are easy to nod along to and hard to actually internalize.
These four problems were hit, diagnosed, and fixed in this exact project — each one is
a genuinely common, generalizable lesson.

### 6a. The 10.5GB image (CPU vs. GPU dependencies)

**What happened**: the backend's `sentence-transformers` dependency, installed the
default way, pulled in a GPU-enabled build of PyTorch — which drags along ~2GB of
NVIDIA CUDA libraries the app will never use (this inverter runs on plain CPU
instances, no GPU anywhere). Image size: 10.5GB.

**The fix**: explicitly install the CPU-only PyTorch build first
(`pip install torch --index-url https://download.pytorch.org/whl/cpu`), *before* the
rest of the dependencies, so pip doesn't later pull the GPU variant as a transitive
dependency. Image size: 2.89GB.

**The lesson**: Python's default package resolution doesn't know what hardware you're
actually deploying to. For any ML-adjacent dependency, check whether you're silently
paying for GPU support you'll never use — this is a very common, very avoidable source
of bloated containers.

### 6b. The editable-install bug (how Python packaging affects file paths)

**What happened**: the app's own code (`db/migrate.py`) locates the Alembic migrations
config file using `Path(__file__).resolve().parents[3]` — i.e., "go up three folders
from wherever this very file is running from." That assumption quietly depended on the
code never being "properly" installed (true for local dev, where `pytest` just adds
`src/` to the Python path directly). The Dockerfile originally did a normal
`pip install .`, which *copies* the source files into Python's `site-packages`
directory — changing where `__file__` actually points, and silently breaking that
path assumption. The container crashed on startup with an Alembic config error.

**The fix**: `pip install -e .` (an **editable install**) instead — this makes the
installed package a *reference* back to the original `src/` files rather than a copy,
so `__file__` still resolves to the real, original location.

**The lesson**: code that derives paths from its own location (`__file__`) is making an
implicit assumption about *how the code got there*. That assumption can be invisible
until you change the deployment method — exactly what happened here. Worth knowing as
a general debugging instinct: "this worked locally but broke in a container" is very
often a path/environment assumption, not a logic bug.

### 6c. The hung-looking container (it wasn't actually hung)

**What happened**: the backend container appeared stuck for several minutes after
"Loading weights: 100%" with near-zero CPU usage, looking exactly like a hang.

**The diagnosis**: rather than assume it was broken, a small timing script was run
*inside the container* that imported and timed each startup stage individually. It
showed the real bottleneck plainly: `DenseIndex` construction (encoding every manual
chunk through the embedding model) took ~30 seconds on this machine's CPU — genuinely
slow, not frozen. A second run (reusing the warmed Hugging Face model cache) confirmed
it: total cold start was a couple of minutes, a cache-warmed restart was 45 seconds.

**The lesson**: "looks hung" and "is hung" are different claims, and the only way to
tell them apart is to actually measure, not assume. `docker stats` (CPU/memory over
time) and a quick in-container timing script are cheap, fast ways to find out which one
you're looking at before spending time debugging a problem that doesn't exist.

### 6d. The SSH timeout that "shouldn't" have happened (public vs. private IP + security groups)

**What happened**: the app's security group explicitly allowed SSH from the Jenkins
instance's security group (§3e) — correct on paper — yet Jenkins' first two deploy
attempts both failed with `Connection timed out` on port 22.

**The real cause**: the `Jenkinsfile` was addressing the app instance by its **public**
IP. Even though both instances are in the same VPC, traffic to a public IP routes out
through the Internet Gateway and back in — and AWS's security-group-source matching
(`UserIdGroupPairs`) only works for traffic that stays entirely *inside* the VPC. Once
traffic leaves through the Internet Gateway, AWS no longer tracks "which security group
did this packet originate from," so the rule silently never matches.

**The fix**: point the Jenkinsfile at the app instance's **private** IP instead — since
both instances share a VPC, that's simple internal routing, and the SG-source rule
applies correctly.

**The lesson**: a security-group-to-security-group rule is an *intra-VPC-only*
mechanism — a detail that's easy to not know exists until it silently fails exactly
like this. The general habit worth keeping: when two of your own resources talk to each
other, prefer their private IPs/internal DNS, not their public ones — it's faster,
free, and (as this incident shows) sometimes the only thing that actually works with
your security rules.

---

## 7. The whole picture, in one diagram

```
 You (git push) ──► GitHub (main branch)
                         ▲
                         │ polls every 5 min
                         │
          ┌──────────────┴───────────────┐
          │   suryasutra-jenkins (EC2)    │
          │   Jenkins, in a container      │
          │   port 8080 — you only         │
          └──────────────┬───────────────┘
                         │ SSH (private IP, SG-to-SG rule)
                         ▼
          ┌──────────────────────────────┐
          │   suryasutra-app (EC2)        │
          │   git pull → docker compose    │
          │   build → up --build           │
          │  ┌──────────┐  ┌────────────┐ │
          │  │ backend  │  │  frontend   │ │
          │  │ FastAPI  │◄─┤  nginx      │ │  port 80 — public
          │  │ :8000    │  │  :80        │ │
          │  └──────────┘  └────────────┘ │
          └──────────────────────────────┘
                         ▲
                         │ HTTP
                   anyone with the link
```

---

## 8. Glossary — the infra terms used above

- **Container / image**: a running instance of a packaged application, vs. the
  packaged template it was started from.
- **Dockerfile**: the recipe for building an image, line by line, each line a cached
  layer.
- **docker-compose**: declares and runs multiple related containers together as one
  stack.
- **Volume**: persistent storage outside a container's own disk, so data survives the
  container being recreated.
- **Region / VPC / subnet / availability zone**: AWS's geographic and network
  hierarchy — a region contains availability zones, a VPC is your private network
  inside a region, a subnet lives in one zone.
- **Security group**: a per-instance virtual firewall; rules can reference an IP range
  or another security group.
- **Public IP vs. private IP**: internet-reachable vs. only-reachable-within-the-VPC.
- **Key pair**: the public/private keypair AWS uses for SSH login instead of passwords.
- **CI/CD**: automatically building/testing/deploying code on every change, instead of
  doing it by hand.
- **Pipeline / Jenkinsfile**: a CI/CD process, defined as versioned code rather than
  manual UI configuration.
- **Webhook vs. polling**: push-based (instant, needs public inbound access) vs.
  pull-based (a short delay, needs no inbound access) ways to detect new commits.

---

## 9. Where to look for more

- `docs/DECISIONS.md`, entries D-42 and D-43 — the full, dated record of every
  decision and incident summarized above, including the ones not expanded on here.
- `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`,
  `docker-compose.prod.yml`, `web/nginx.conf` — the actual configuration.
- `Jenkinsfile`, `infra/app-userdata.sh`, `infra/jenkins-userdata.sh` — the actual
  deploy automation.
