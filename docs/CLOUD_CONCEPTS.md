# SuryaSutra — cloud, containers, CI/CD & the backend's own concepts, explained

This is the companion to `docs/NLP_CONCEPTS.md`. That one explains what the app *does*
(the retrieval/selection/generation pipeline); this one explains how it actually
**runs** — locally, how it gets from your laptop to a public URL, what each
infrastructure piece is for, and (§9 onward) the backend/API design concepts and full
tech-stack breakdown underneath the "Database Connectivity," "Backend Functionality,"
and "Presentation & Explanation" parts of a typical project rubric. Same rule as
CLAUDE.md's teaching mandate throughout: concept → why → alternative → what we
actually built, grounded in real file paths and the real problems we hit (not
hypothetical ones).

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

### 4e. What triggers a build: polling, GitHub Actions, and a webhook — and how this evolved

The first version of this pipeline used **SCM polling only**: Jenkins itself checks
GitHub every 5 minutes (`H/5 * * * *`, the pipeline's trigger) and starts a build if
anything changed. Slower (up to a 5-minute delay) but needs zero public inbound access
to Jenkins — the right tradeoff for a first pass.

**This project later asked for a "complete" pipeline**, meaning: a CI gate (tests must
pass before anything deploys) and near-instant triggering, not a 5-minute wait. Getting
both meant a real, explicit tradeoff, confirmed before making it: real-time triggering
needs *something* to reach Jenkins the moment a push happens, and Jenkins locked down to
one IP (§3e) can't be reached by anything external. Three ways to resolve that were on
the table:

1. **A raw GitHub webhook straight to Jenkins** — GitHub's own servers POST to Jenkins
   the instant you push. Fastest, but means teaching Jenkins' GitHub plugin to validate
   GitHub's webhook payloads, and GitHub's webhook-sender IP ranges are numerous and
   change, so "only allow GitHub's IPs" isn't a precise, stable firewall rule in practice.
2. **GitHub Actions as the middleman** (what was actually built) — a free, hosted CI
   runner (GitHub's own CI/CD product, see §4f) runs the tests *first*, and only on
   success calls Jenkins' own remote-build-trigger URL. This gets the CI gate "for free"
   as a side effect of needing a trigger at all, and the only network requirement is
   "Jenkins is reachable on one port," not "Jenkins can validate GitHub's specific
   request format."
3. **Drop Jenkins from the live trigger path entirely** and have GitHub Actions deploy
   directly — rejected; Jenkins was an explicit, separate ask (§4a) and removing it from
   the real pipeline would make the earlier Jenkins setup pointless busywork.

**Decision: option 2.** `suryasutra-jenkins-sg` now allows inbound 8080 from anywhere
(`0.0.0.0/0`), not just one IP — a real, permanent increase in attack surface, accepted
knowingly rather than discovered later. **The thing actually protecting Jenkins now is
authentication, not network isolation** — see §4f for exactly how that's structured, and
why the obvious-looking shortcut (the job's own simple `?token=` URL) didn't work.

The old 5-minute SCM poll was **deliberately left running alongside** the new trigger,
not removed — if the push-based trigger ever silently failed, the poll still catches the
same commit within 5 minutes. Belt-and-suspenders, not either/or.

### 4f. GitHub Actions, CI gates, and why a working build still needs the right account

**GitHub Actions**, in one sentence: a CI/CD runner built into GitHub itself — you
commit a YAML file (`.github/workflows/ci-cd.yml`) describing jobs to run, GitHub spins
up a disposable virtual machine per job, runs them, and reports pass/fail right on your
commit/PR. No separate server to provision (unlike Jenkins, which needed its own EC2
instance, §4b) — the tradeoff is less control over the exact machine, which doesn't
matter for "run `pytest`."

**The three jobs, in `.github/workflows/ci-cd.yml`:**

```yaml
jobs:
  backend:   # ruff (lint) -> mypy (type-check) -> pytest (139 tests)
  frontend:  # oxlint (lint) -> vite build
  trigger-deploy:
    needs: [backend, frontend]              # <- the actual CI gate
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    steps:
      - run: curl -X POST -u "github-actions:${{ secrets.JENKINS_TRIGGER_TOKEN }}" \
             "${{ secrets.JENKINS_URL }}/job/suryasutra-deploy/build"
```

`needs: [backend, frontend]` is the entire CI gate — GitHub Actions won't even start a
job until everything it `needs` has succeeded, so a failing test genuinely blocks the
`curl` call that would otherwise tell Jenkins to deploy. **`secrets.*`** are GitHub's own
encrypted secret store (Settings → Secrets and variables → Actions) — values set once in
GitHub's UI, injected into the workflow at run time, never visible in the YAML file
itself or in any log output.

**Why calling Jenkins needed its own dedicated account, not just "add a token to the
job."** Jenkins' remote-trigger feature normally works via a simple
`/job/NAME/build?token=SECRET` URL with no login at all — the obvious thing to try
first. It was tried first here, and it failed with a `403` ("Permission you need:
`hudson.model.Hudson.Read`") — because this Jenkins has
`denyAnonymousReadAccess=true`: an anonymous request is rejected before Jenkins even
checks whether the token is valid. The fix was a real **service account**: a dedicated
Jenkins user (`github-actions`), created headlessly (see below), authenticating via
**HTTP Basic Auth with an API token** instead of a password. An **API token** is a
long random string Jenkins can generate for an account, usable only for
API/script access (not for logging into the web UI), and independently revocable without
touching that account's real password — exactly the property you want for something a
CI pipeline will store in a secret.

**One honest nuance, not glossed over**: this Jenkins' authorization model
(`FullControlOnceLoggedInAuthorizationStrategy` — "any logged-in account can do
anything") means `github-actions` isn't actually *restricted* to "only trigger this one
job" — it has full control, same as any human account here. The real benefit of a
separate account under this model is independent **rotation and revocation** (this one
token can be invalidated without affecting any human's login), not reduced privilege. A
stricter setup (matrix-based authorization, scoped per-job permissions) would close that
gap — noted as a real, open improvement, not pretended to already be solved.

**How the account, its token, and (later) a forgotten human password were all handled
without ever typing a secret into a chat or a visible command**: Jenkins supports
`init.groovy.d` — a folder where any `.groovy` script dropped in runs automatically, once,
the next time Jenkins starts, with full administrator privileges (no login required,
since Jenkins itself is executing it as part of its own startup). A script here can
create a user, generate an API token, or reset a password — write the result to a file
*inside* the Jenkins container, which then gets copied out to a local file (`scp`
file-to-file, never `cat` to a terminal) and deleted from the container — the exact same
"generate once, never display" handling as the original SSH key (§3g).

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

## 6. Real incidents, and what each one teaches

Abstract cloud concepts are easy to nod along to and hard to actually internalize.
Every problem below was actually hit, diagnosed, and fixed in this exact project —
each one is a genuinely common, generalizable lesson, not a hypothetical.

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

### 6e. The deploy that "succeeded" but failed its own health check (burstable CPU credits)

**What happened**: after both EC2 instances were restarted and the new GitHub
Actions → Jenkins pipeline (§4e/4f) was wired up, the very first real deploy's
**build and container startup both completed correctly** — Jenkins' own log showed
images built, old containers recreated, new ones started — yet the pipeline's own
**smoke test step failed** (`curl -sf .../api/health`, exit code 22), and the app
genuinely returned a live `502 Bad Gateway` from nginx for several minutes afterward.

**The diagnosis, done with real data, not a guess**: SSH'd into the app instance (via
the Jenkins instance as a **jump host** — see §6f below) and ran `free -h` /
`docker stats`: 485MB of the instance's 2GB swap was in active use on a plain
**916MB-RAM `t3.micro`**, with the backend container's process accumulating almost no
new CPU time between checks — not "frozen," just extremely slow. AWS's own CloudWatch
metric `CPUCreditBalance` for that instance confirmed why: **~0.006 to 0.97 credits
remaining**, when a healthy instance normally has dozens.

**The concept**: `t3` instances are **burstable** — they get a baseline (a fraction of
one vCPU) plus a slowly-replenishing pool of "CPU credits" that let them burst to full
speed for short periods. Heavy, sustained work (here: Jenkins' `docker compose build`
immediately followed by the backend's own CPU-heavy startup — loading an embedding
model and encoding the whole manual into vectors, §6c) can burn through that credit
pool faster than it refills. Once credits hit zero, AWS throttles the instance down to
its tiny baseline rate — the instance isn't broken, it's deliberately slowed down by
AWS's own billing model.

**The fix, and the real tradeoff behind it**: resized the instance from `t3.micro` to
`t3.small` (AWS CLI: stop the instance → `modify-instance-attribute --instance-type` →
start it again; its private IP stayed the same, so nothing else needed updating).
`t3.small` isn't AWS free-tier eligible — a real, ongoing hourly cost (roughly
$0.02/hr per third-party trackers, not AWS's own price list) versus `t3.micro`'s free
750 hours/month. This was a genuine cost-vs-reliability decision, not something to pick
silently — confirmed explicitly before making it. After the resize: 0 swap in use,
and a fresh deploy's smoke test passed cleanly.

**The lesson**: a "stuck" cloud instance isn't always a code bug — on burstable
instance types specifically, check the CPU credit balance (`CPUCreditBalance` in
CloudWatch) before assuming the application hung. This is a very common trap with
`t2`/`t3` free-tier instances under any real load (a Docker build *and* an ML model
load, back to back, is exactly the kind of burst this instance class isn't sized for).

### 6f. Reaching a locked-down instance without opening a new door (SSH jump host)

**What happened**: debugging §6e meant needing an SSH shell on the app instance — but
its security group only allows SSH from one specific IP (§3e), and that session's own
outbound IP didn't match it. The tempting fix — add a new inbound rule for whatever IP
happens to be asking — was tried once for a different, lower-stakes case, but widening
SSH access on a second security group was correctly treated as a bigger, more
deliberate decision and avoided here.

**The actual fix**: the app instance's security group *already* allows SSH from
anything carrying the Jenkins security group's identity (the SG-to-SG rule from §3e/§6d
exists for exactly this). Since there was already SSH access to the *Jenkins* box, that
box could be used as a **jump host** (also called a bastion host) — a stepping-stone
server you SSH into first, which then forwards the connection on to a second,
otherwise-unreachable machine:

```bash
ssh -i key.pem \
    -o ProxyCommand="ssh -i key.pem -W %h:%p ec2-user@<jenkins-public-ip>" \
    ec2-user@<app-private-ip>
```

`ProxyCommand` tells the local `ssh` client: "don't connect directly — first SSH to the
jump host, then tunnel the raw TCP connection through it to the real destination." The
private key never leaves the local machine; the jump host just relays encrypted bytes
it can't read.

**The lesson**: "I need access to debug this" doesn't always mean "open a new inbound
rule." If a network path to the target already exists through something you can already
reach, a jump host gets you there without touching the firewall at all — the more
reversible, smaller-blast-radius option, and the standard pattern in real production
environments for reaching instances that are deliberately never exposed to begin with.

### 6g: CI passed locally, failed in GitHub Actions — an untracked dependency

**What happened**: `mypy src` passed cleanly on the local development machine both
before and immediately after writing the new GitHub Actions workflow — yet the very
first real run of that workflow on GitHub's own servers failed at the exact same
`mypy` step, with `Library stubs not installed for "yaml" [import-untyped]`.

**The real cause**: a package called `types-PyYAML` (type *stubs* for the `PyYAML`
library — metadata that tells `mypy` what shapes `yaml.safe_load()` etc. return,
without which mypy can't type-check code that uses it) was installed in the local
`.venv` at some earlier point, but was never added to `pyproject.toml`'s own list of
declared dev dependencies. Locally, it was just silently *there*. GitHub Actions starts
from a completely empty virtual machine every single run — it only installs exactly
what `pyproject.toml` says to install, so the gap was invisible until a genuinely clean
environment ran the same check.

**The fix, verified rather than assumed**: added `"types-PyYAML>=6.0"` to
`pyproject.toml`'s `dev` dependencies. Confirmed it was the real, sufficient fix by
*reproducing the failure locally first* — uninstalled `types-PyYAML` from the local
venv, confirmed `mypy` now failed the same way locally, reinstalled via
`pip install -e ".[dev]"` (which reads `pyproject.toml`), and confirmed `mypy` passed
again — proving the fix works from the declared dependency list alone, not from
whatever happened to already be sitting in one developer's machine.

**The lesson**: "it works on my machine" is a real, common failure mode precisely
*because* a local environment accumulates packages over time that were never recorded
anywhere. A CI system that builds from a clean environment on every run is valuable
exactly because it catches this — every dependency a project actually needs must be
written down somewhere a machine reads (`pyproject.toml`, `package.json`), not just
present on whichever computer happened to get there first.

---

## 7. The whole picture, in one diagram

```
 You (git push) ──► GitHub (main branch)
                         │
                         ▼
          ┌───────────────────────────────┐
          │   GitHub Actions (§4f)         │
          │   backend: ruff/mypy/pytest    │
          │   frontend: oxlint/vite build  │
          └───────────────┬───────────────┘
                   needs: both succeed
                           │ POST .../build
                           │ (Basic Auth: github-actions + API token)
                           ▼
          ┌───────────────────────────────┐◄── (fallback: still polls
          │   suryasutra-jenkins (EC2)    │     GitHub every 5 min too)
          │   Jenkins, in a container      │
          │   port 8080 — now public,      │
          │   token-protected (§4e/4f)     │
          └──────────────┬───────────────┘
                         │ SSH (private IP, SG-to-SG rule)
                         ▼
          ┌──────────────────────────────┐
          │   suryasutra-app (EC2)        │
          │   t3.small (§6e)               │
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
- **Webhook vs. polling vs. a CI-triggered call**: push-based (instant, needs public
  inbound access), pull-based (a short delay, needs no inbound access), or a hosted CI
  runner calling the deploy tool itself only after tests pass (§4e/4f) — what this
  project actually settled on.
- **CI gate**: a later step (e.g. "deploy") made conditional on an earlier step (e.g.
  "tests") succeeding — GitHub Actions' `needs:` keyword implements this directly.
- **Service account**: a dedicated login for a tool or pipeline to use, kept separate
  from any human's own account so it can be rotated or revoked independently.
- **API token**: a long random credential an account can generate for
  script/API access, usable in place of (and independently revocable from) that
  account's actual password.
- **Burstable instance (`t2`/`t3`)**: an instance type with a low guaranteed baseline
  CPU rate plus a pool of "credits" that let it run faster temporarily — sustained heavy
  work can exhaust the pool and throttle the instance hard (§6e).
- **Jump host / bastion host**: a reachable server used purely to relay an SSH
  connection on to a second, otherwise-unreachable server, without opening new direct
  access to that second server (§6f).

---

## 9. REST APIs and CRUD — the concepts behind the backend's data layer

### 9a. REST, in practice

**Concept.** REST (Representational State Transfer) is a convention for structuring a
web API around *resources* (nouns — an alarm, a feedback entry) and a small, fixed set
of *HTTP methods* that act on them, instead of inventing a new verb-named endpoint for
every action. The method says what kind of thing is happening; the URL says what it's
happening to.

| Method | Means | Example in this project |
|---|---|---|
| `GET` | Read, never changes anything | `GET /alarms`, `GET /feedback` |
| `POST` | Create something new | `POST /triage` (creates a `triage_runs` row), `POST /feedback` |
| `PATCH` | Partially update an existing thing | `PATCH /feedback/{id}` |
| `DELETE` | Remove something | `DELETE /feedback/{id}` |

**Why this convention, not a pile of custom-named endpoints** (e.g.
`/getAlarms`, `/createFeedback`, `/removeFeedback`)? Because the method + URL pair is
self-describing and predictable — any client (or any new developer) can guess that
`DELETE /feedback/7` deletes feedback entry 7, without reading documentation. FastAPI
also uses this structure to auto-generate the interactive API docs you can see at
`/docs` once the backend is running.

**Status codes carry meaning too**: `200` (success), `404` (the thing you asked for
doesn't exist — e.g. `GET /feedback/999999`), `422` (the request body failed
validation — e.g. an invalid `outcome` value). These aren't picked arbitrarily; FastAPI
derives them automatically from Pydantic validation (`422`) and from explicit
`HTTPException` calls in the route functions (`404`) — see
`src/suryasutra/api/main.py`.

### 9b. CRUD — and why it's deliberately *not* everywhere in this app

**Concept.** CRUD (Create, Read, Update, Delete) names the four basic operations any
persistent data usually needs. A common rubric question is simply "does the app
support all four, somewhere real" — and it's worth being precise about *where*, not
just asserting yes.

**Where full CRUD actually lives in this project**: the `feedback` table.

| Operation | Endpoint | What it does |
|---|---|---|
| Create | `POST /feedback` | A technician submits an outcome (fixed / not fixed / wrong step / unsafe) after a triage answer |
| Read | `GET /feedback` | List every submitted feedback entry |
| Update | `PATCH /feedback/{feedback_id}` | Correct a submitted outcome or note |
| Delete | `DELETE /feedback/{feedback_id}` | Remove an entry entirely |

All four are driven by a real, working UI: `web/src/components/FeedbackForm.tsx`
(Create) and `web/src/pages/FeedbackList.tsx` (Read, inline Update, Delete) — not just
callable via `curl`.

**Why `alarms` and `triage_runs` deliberately *don't* get Update/Delete.** This isn't
an oversight — it's a direct consequence of what those tables actually represent:

- `alarms` is the seeded demo dataset (`data/synthetic/alarms.json`) — reference data
  everyone's queue is built from. Letting anyone edit or delete rows here would mean
  the demo data silently drifts from what's documented as synthetic and labelled.
- `triage_runs` is an **audit trail** — the whole point of logging every run (model
  used, tokens spent, exact answer given) is so it can be inspected later and trusted
  as *what actually happened*. Making it editable would undermine the one property
  that makes an audit trail useful: that it can't be quietly rewritten after the fact.

`feedback`, on the other hand, is genuinely user-generated opinion about a run's
outcome — a technician *should* be able to correct a mis-click or retract a note.
Giving CRUD to the table where it makes sense, and deliberately not giving it to
tables where mutability would work against the project's own design (D-06, D-11's
"never fabricate/never silently alter the record" principles), is the actual design
decision — see `docs/DECISIONS.md` D-47 for the full reasoning.

### 9c. How a request actually reaches the database

Concretely, for `PATCH /feedback/{feedback_id}` (`src/suryasutra/api/main.py`):

1. FastAPI matches the incoming request's method + URL pattern to the
   `update_feedback` Python function, and parses the JSON body into a
   `FeedbackUpdateRequest` (a Pydantic model, `src/suryasutra/api/schemas.py`) —
   if the body doesn't match that shape, FastAPI rejects it with `422` before your
   code even runs.
2. The function opens a database session (`get_session()`,
   `src/suryasutra/db/session.py`) and looks up the row by id
   (`session.get(Feedback, feedback_id)`). If it doesn't exist, `404`.
3. It updates only the fields that were actually provided (`if req.outcome is not
   None: ...`) — a `PATCH` is a *partial* update; a field left out of the request
   body stays unchanged, unlike a `PUT`, which would conventionally replace the whole
   resource.
4. `get_session()`'s context manager commits the change automatically when the
   function returns successfully, or rolls it back if anything raised an exception —
   so a request either fully succeeds or leaves no partial change behind.

## 10. Client-side identification vs. real authentication

**Concept.** "Who is using this right now" can be answered two very different ways:

- **Authentication**: cryptographically verifying an identity — a password checked
  against a hashed value stored server-side, then a session token or cookie that
  proves "this browser already proved who it is" on every later request. This is what
  a real "login" means.
- **Identification**: just *asking* who someone is, and remembering the answer,
  without verifying it against anything. Anyone can type any name.

**What this project actually has** (`web/src/useIdentity.ts`,
`web/src/components/SignInGate.tsx`): identification only. A name and role, typed
once, stored in the browser's `localStorage`. No password, no server-side account, no
session token — the backend's `POST /feedback` endpoint trusts whatever `user_role`
string the frontend sends it.

**Why not build real authentication to make "login" literally true?** Because a login
screen that *looks* secure but isn't would be actively misleading — worse than openly
having no authentication at all. Real auth needs a `users` table with hashed
passwords, a session/token mechanism, and routes protected by checking that token —
none of which exists yet, and building a convincing-looking but fake version of it
would be the kind of dishonesty this project's own rules (D-11: never fabricate) are
specifically about avoiding. The sign-in screen's own copy says this plainly: *"this
identifies your feedback, it isn't a password-protected account."*

**The practical reason it exists at all**: before it was added, `POST /feedback`
had no real source for `user_role` in the UI at all — this screen is what makes that
field genuinely meaningful (a real human typed it) instead of a hardcoded placeholder
string, while being honest about exactly what security guarantee it does and doesn't
provide.

## 11. Presentation & Explanation — the full tech stack, module by module

This is the detailed version of rubric criterion 6: not just "we used React," but
*what it is, why it specifically (not the next-most-obvious alternative), and what
module we actually built with it.* Everything below is a real, installed dependency —
cross-check any of it against `pyproject.toml` or `web/package.json`. The AI/retrieval
stack (BM25, dense embeddings, the LLM, FAISS) is deliberately not repeated here in
depth — that's `docs/NLP_CONCEPTS.md`'s whole job; §11.5 below just places it in the
bigger picture.

### 11.1 Backend

| Tech | What it is | Why this, not the alternative | What we built with it |
|---|---|---|---|
| **Python 3.11+** | General-purpose language | The entire ML/NLP ecosystem (embeddings, retrieval, LLM SDKs) is Python-first; a Node or Go backend would mean reimplementing or shelling out to Python anyway for the actual AI pipeline | All of `src/suryasutra/` |
| **FastAPI** | Async Python web framework | Validates request/response shapes automatically from Python type hints (via Pydantic) and generates the interactive `/docs` page for free — a Flask equivalent needs a separate library (e.g. Flask-RESTX) bolted on for both | `src/suryasutra/api/main.py` — 9 routes (§9 above) |
| **Pydantic v2** | Data validation library | FastAPI is built around it; a malformed request body is rejected with a `422` and a precise error *before* any of our code runs, instead of our code having to check `if "outcome" not in body: ...` by hand everywhere | `src/suryasutra/api/schemas.py`, `src/suryasutra/generation/schema.py` — every request/response shape in the project |
| **SQLAlchemy 2.0** | Python ORM (Object-Relational Mapper) | Lets the same model classes (`src/suryasutra/db/models.py`) target SQLite now and Postgres later by changing one connection string (`DATABASE_URL`), instead of hand-writing SQL that's tied to one database's dialect | `Alarm`, `TriageRun`, `Usage`, `Feedback` tables |
| **Alembic** | Database migration tool (pairs with SQLAlchemy) | Every schema change (e.g. adding the `feedback` table) is a versioned, re-runnable script instead of a manual `ALTER TABLE` someone has to remember to run on every machine | `src/suryasutra/db/alembic/versions/` — 2 migrations so far |
| **SQLite** | Embedded, file-based database | Needs zero setup — no separate database server to install or configure for local development or grading. Swapped for Postgres only at pilot stage, when multiple concurrent users actually need it (see `docs/DECISIONS.md` D-35) | `data/processed/suryasutra.db` |

### 11.2 Frontend

| Tech | What it is | Why this, not the alternative | What we built with it |
|---|---|---|---|
| **React 18 + TypeScript** | UI library + typed JavaScript | Component model matches this app's structure well (alarm row → triage panel → citation chip, each independently re-usable); TypeScript catches a wrong prop type or a typo'd field name at build time instead of at runtime in the browser | Every file in `web/src/` |
| **Vite** | Frontend build tool / dev server | Near-instant hot-reload during development (changes appear in the browser in milliseconds, not after a multi-second rebuild) — a big, felt difference from older bundlers (Webpack/CRA) when iterating on UI | `web/vite.config.ts`, `npm run dev` / `npm run build` |
| **React Router** | Client-side routing | Without it, `/` and `/app` would have to be the same page faking two states — real URLs mean the landing page and the app are genuinely separate, bookmarkable, shareable locations | `/` → `LandingPage`, `/app` → `AppShell` (`web/src/App.tsx`) |
| **Tailwind CSS v4** | Utility-first CSS framework | Colors/spacing/radii are defined once as CSS variables (`web/src/styles/tokens.css`) and consumed as plain class names (`bg-surface-1`, `text-danger`) everywhere — changing the whole theme means editing one file, not hunting through every component's custom CSS | The entire visual design system (dark "control room" + light "Field mode" themes) |
| **TanStack Query** | Server-state/data-fetching library | Handles loading/error/cached states for every API call automatically (`useQuery`, `useMutation`) — without it, every component would hand-roll its own `isLoading`/`try-catch`/re-fetch-after-mutation logic | Every data fetch in the app (`getAlarms`, `runTriage`, `listFeedback`, etc.) |
| **Radix UI** | Unstyled, accessible component primitives | `Tabs`, `Dialog` come with correct keyboard navigation, focus trapping, and ARIA roles already solved — building that correctly by hand is a well-known source of subtle accessibility bugs | Tab navigation (`AppShell.tsx`), the citation source panel (`SourcePanel.tsx`) |
| **Motion** (successor to Framer Motion) | React animation library | Declarative — animations are described as data (`initial`/`animate`/`transition` props) instead of imperative DOM manipulation, and it respects `prefers-reduced-motion` with one hook (`useReducedMotion`) instead of hand-written media-query logic everywhere | Page transitions, the landing page's scroll-triggered reveals, the 3D-tilt glass cards |
| **Lucide React** | Icon library | One consistent stroke style across the whole app (safety warnings, theme toggle, feedback edit/delete icons) instead of mixing emoji and ad-hoc SVGs | Icons throughout `web/src/components/` and `web/src/pages/` |
| **Recharts** | Charting library | A thin, React-native wrapper over SVG charts — enough for the one bar chart the dashboard needs, without pulling in a much heavier general-purpose visualization library | `web/src/pages/Dashboard.tsx`'s cost-per-method chart |

### 11.3 DevOps, deployment & version control

Each of these has its own full section earlier in this document — this is the "why,
briefly" index:

- **Docker** (§2) — packages the exact Python/Node dependency versions so the app runs
  identically on this machine, a grader's machine, or an AWS server, instead of
  hoping everyone's local environment happens to match.
- **AWS EC2** (§3) — the actual computer the public demo link runs on, chosen (as a
  category) because it's the most widely-used cloud platform to have hands-on
  experience with.
- **Jenkins** (§4) — automates "a new commit is pushed → the live server rebuilds and
  redeploys itself," so demoing a new version never means manually SSHing in and
  running commands by hand.
- **Git + GitHub** (§5) — every change in this project is a committed, attributable,
  revertable snapshot; GitHub is where the single source of truth (`main` branch)
  lives, and what Jenkins actually watches for changes.

### 11.4 Testing

| Tech | What it is | Why this, not the alternative | What we built with it |
|---|---|---|---|
| **pytest** | Python test runner | The de-facto standard for Python; plain `assert` statements instead of a verbose `self.assertEqual(...)` API | 139 tests across `tests/unit/` and `tests/integration/` |
| **Hypothesis** | Property-based testing | Instead of writing one example input per test, it generates *hundreds* of random inputs looking for one that breaks an invariant — used specifically because the selector's core promise ("never exceeds the token budget," "never answers with uncovered mandatory evidence") needs to hold for *every* possible input, not just the one example we thought to write | Selector invariant tests (see `docs/NLP_CONCEPTS.md` §5 for what those invariants are) |
| **Playwright** | Real-browser end-to-end testing | Unit tests mock the backend; Playwright actually launches a real Chromium browser, clicks real buttons, and hits the real FastAPI server (and, for some tests, makes a real Groq API call) — the only way to catch a bug that only exists in the real integration, like the sign-in-gate routing issue these tests were specifically updated to catch | `web/e2e/` — 5 tests: landing, triage, compare, dashboard, feedback CRUD |

### 11.5 AI/ML (the part `docs/NLP_CONCEPTS.md` covers in full)

Briefly, for completeness: **Groq** (LLM provider, chosen for low cost/speed),
**sentence-transformers** + **FAISS** (dense/semantic retrieval), **rank-bm25**
(lexical retrieval), **PyMuPDF** (PDF parsing). Full why/how for each is in
`docs/NLP_CONCEPTS.md` §4 and §6 — that's where the project's actual research
contribution lives, not in this infrastructure-focused document.

---

## 12. Rubric compliance — what's implemented, where, and why

This project was checked against a 6-criterion, 20-mark grading rubric. Rather than
just asserting "done," here's exactly what satisfies each criterion and where to find
it.

| # | Criterion | Marks | What satisfies it |
|---|---|---|---|
| 1 | Project Setup & Structure | 2 | `pyproject.toml` (Python deps), `web/package.json` (frontend deps), a clear `src/suryasutra/` module layout (full tree in `CLAUDE.md` §8), `docker-compose.yml` for one-command startup, `README.md`'s quickstart. |
| 2 | UI Design (home/login/dashboard, navigation) | 4 | Landing page (`/`, `web/src/landing/`) as home; `SignInGate` (§10 above) as the identification/login screen; `Dashboard` tab; Radix `Tabs` navigation between Alarm queue / Feedback / Dashboard (`web/src/AppShell.tsx`) — all with working routing (`react-router-dom`, added per `docs/DECISIONS.md` D-46). |
| 3 | Backend Functionality | 4 | FastAPI (§9 above) — 9 real routes across alarms, triage, runs, usage stats, and full feedback CRUD; the actual triage pipeline (retrieval → selection → generation, `docs/NLP_CONCEPTS.md`) is real server-side logic, not a stub. |
| 4 | Database Connectivity (CRUD working) | 3 | SQLite via SQLAlchemy (`src/suryasutra/db/`), Alembic migrations. Full Create/Read/Update/Delete demonstrated on the `feedback` table (§9b above), with both backend tests and a real browser-driven UI for every operation. |
| 5 | Testing & Debugging | 3 | 139 backend tests (`pytest`, unit + integration), 5 end-to-end browser tests (`Playwright`, against the real backend and real LLM calls, not mocks) — all passing. The app was driven live in a real browser (sign in → triage → submit/edit/delete feedback) with zero console errors before this was called done. Those same checks now also run automatically on every push via GitHub Actions (§4f) — debugging real CI-vs-local mismatches (§6g) and a real instance-sizing failure (§6e) is documented, not hidden. |
| 6 | Presentation & Explanation | 4 | §11 above (the full tech-stack why/what) plus `docs/NLP_CONCEPTS.md` — concept → why → alternative → real implementation, for every non-obvious choice in the project, with file references throughout. `docs/DECISIONS.md` has the full dated reasoning behind every one. |

**Status: all six criteria have real, verifiable evidence** — the two genuine gaps
found when this was first checked (no Update/Delete anywhere in the API, and
`POST /feedback` having no frontend at all) were identified by reading the actual code
rather than assuming, then fixed and verified end-to-end, not just patched to look
complete (`docs/DECISIONS.md` D-47, `docs/PROGRESS.md`'s corresponding entry). Both
the backend test suite and the frontend build were re-verified as recently as this
same writing session — 139/139 passing, build clean.

---

## 13. Where to look for more

- `docs/DECISIONS.md`, entries D-42, D-43, D-47, and **D-48** — the full, dated record
  of every decision and incident summarized above, including the ones not expanded on
  here. D-48 specifically covers the GitHub Actions + Jenkins push-trigger work and the
  `t3.small` resize in §4e-4f and §6e-6g.
- `Dockerfile.backend`, `Dockerfile.frontend`, `docker-compose.yml`,
  `docker-compose.prod.yml`, `web/nginx.conf` — the actual deploy configuration.
- `Jenkinsfile`, `infra/app-userdata.sh`, `infra/jenkins-userdata.sh` — the actual
  deploy automation.
- `.github/workflows/ci-cd.yml` — the GitHub Actions CI gate and Jenkins trigger
  referenced in §4f.
- `src/suryasutra/api/main.py`, `src/suryasutra/api/schemas.py` — every route and
  request/response shape referenced in §9.
- `web/src/useIdentity.ts`, `web/src/components/SignInGate.tsx` — the identification
  flow referenced in §10.
- `pyproject.toml`, `web/package.json` — the exact, versioned dependency list behind
  every "why we chose this" claim in §11.
