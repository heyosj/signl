export default function Home() {
  const setupCommand = [
    "git clone https://github.com/heyosj/signl.git",
    "cd signl",
  ].join("\n");

  const envCommand = [
    "export DISCORD_WEBHOOK_URL=\"https://discord.com/api/webhooks/...\"",
    "export SLACK_WEBHOOK_URL=\"https://hooks.slack.com/services/...\"",
    "export WEBHOOK_URL=\"https://hooks.example.com/signl\"",
  ].join("\n");

  const exampleConfig = [
    "version: 1",
    "",
    "stack:",
    "  cloud:",
    "    - azure",
    "    - aws",
    "    - gcp",
    "",
    "  languages:",
    "    - python",
    "    - javascript",
    "    - typescript",
    "    - powershell",
    "    - go",
    "",
    "  packages:",
    "    npm:",
    "      - axios",
    "      - react",
    "      - lodash",
    "      - express",
    "    pip:",
    "      - requests",
    "      - django",
    "      - flask",
    "      - pydantic",
    "      - azure-identity",
    "    go:",
    "      - gin",
    "      - cobra",
    "",
    "  services:",
    "    - entra-id",
    "    - intune",
    "    - azure-sentinel",
    "    - kubernetes",
    "    - docker",
    "    - postgresql",
    "    - redis",
    "",
    "  keywords:",
    "    - kerberos",
    "    - ntlm",
    "    - active directory",
    "    - oauth",
    "    - saml",
    "",
    "notifications:",
    "  discord:",
    "    webhook_url: \"${DISCORD_WEBHOOK_URL}\"",
    "",
    "settings:",
    "  poll_interval_minutes: 15",
    "  state_file: \"./state.json\"",
    "  include_low_severity: false",
    "  max_results_per_feed: 200",
    "  request_timeout_seconds: 20",
    "  user_agent: \"security-stack-notifier/0.1\"",
  ].join("\n");

  return (
    <>
      <div className="orb orb-one"></div>
      <div className="orb orb-two"></div>
      <div className="grid"></div>

      <header className="hero">
        <nav className="nav">
          <span className="logo">signl</span>
          <div className="nav-links">
            <a href="#how">How it works</a>
            <a href="#setup">Setup</a>
            <a href="#config">Config</a>
          </div>
        </nav>

        <div className="hero-content">
          <div className="hero-text">
            <p className="eyebrow">Minimal, robust, zero noise</p>
            <h1>Only the security alerts that match your stack.</h1>
            <p className="lead">
              Define your cloud, packages, services, and dependency sources once.
              The notifier scores and prioritizes alerts, then routes them to
              Slack, Discord, or a webhook only when they apply to your environment.
            </p>
            <div className="cta-row">
              <a className="cta" href="#setup">
                Get set up
              </a>
              <a className="cta ghost" href="#config">
                See the config
              </a>
            </div>
            <div className="stat-row">
              <div>
                <p className="stat">10+</p>
                <p className="stat-label">
                  Feeds supported (NVD, GHSA, MSRC, CISA, OSV, RSS, HN)
                </p>
              </div>
              <div>
                <p className="stat">0</p>
                <p className="stat-label">Noise. Alerts only when relevant.</p>
              </div>
            </div>
          </div>

          <div className="hero-card">
            <div className="card-header">
              <span>Live match</span>
              <span className="pill">Matched</span>
            </div>
            <h3>CVE-2024-XXXXX: Critical in lodash</h3>
            <p>
              Prototype pollution vulnerability allowing remote code execution on
              affected versions.
            </p>
            <div className="chip-row">
              <span className="chip">Package: lodash</span>
              <span className="chip">Priority: P0 (92)</span>
              <span className="chip">Source: NVD</span>
            </div>
            <div className="reason">
              Why you are seeing this: Direct dependency match
            </div>
          </div>
        </div>
      </header>

      <main>
        <section id="how" className="section">
          <div className="section-title">
            <p className="eyebrow">How it works</p>
            <h2>Signal, filtered by your stack.</h2>
          </div>
          <div className="steps">
            <div className="step">
              <span className="step-number">01</span>
              <h3>Describe your stack</h3>
              <p>List clouds, packages, services, and dependency sources in YAML.</p>
            </div>
            <div className="step">
              <span className="step-number">02</span>
              <h3>Poll trusted feeds</h3>
              <p>NVD, GitHub advisories, and MSRC updates are checked on a schedule.</p>
            </div>
            <div className="step">
              <span className="step-number">03</span>
              <h3>Match, score, notify</h3>
              <p>Matches are scored by priority, then sent to your chosen notifiers.</p>
            </div>
          </div>
        </section>

        <section id="setup" className="section">
          <div className="section-title">
            <p className="eyebrow">Setup</p>
            <h2>Set it up in three simple steps.</h2>
          </div>
          <div className="setup-stack">
            <div className="setup-step">
              <div className="setup-step-header">
                <span className="step-number">01</span>
                <h3>Clone the repo</h3>
              </div>
              <p>
                Get the code locally and move into the project directory.
              </p>
              <pre>
                <code>{setupCommand}</code>
              </pre>
            </div>
            <div className="step-arrow" aria-hidden="true"></div>
            <div className="setup-step">
              <div className="setup-step-header">
                <span className="step-number">02</span>
                <h3>Install dependencies</h3>
              </div>
              <p>Use a virtual environment to avoid system Python conflicts.</p>
              <pre>
                <code>
                  {`python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt`}
                </code>
              </pre>
            </div>
            <div className="step-arrow" aria-hidden="true"></div>
            <div className="setup-step">
              <div className="setup-step-header">
                <span className="step-number">03</span>
                <h3>Create config.yaml + run</h3>
              </div>
              <p>For testing, add your stack + notify targets, then run once.</p>
              <pre>
                <code>
                  {`python -m src.main --init-config --config ./config.yaml\n${envCommand}\nrm -f state.json\npython -m src.main --config ./config.yaml --once`}
                </code>
              </pre>
            </div>
            <div className="step-arrow" aria-hidden="true"></div>
            <div className="setup-step accent">
              <div className="setup-step-header">
                <span className="step-number">+</span>
                <h3>Optional: Docker or cron</h3>
              </div>
              <p>Run in Docker for a clean host, or cron for a lightweight schedule.</p>
              <pre>
                <code>
                  {`docker run \\\n  -v ./config.yaml:/app/config.yaml \\\n  -v ./state.json:/app/state.json \\\n  security-stack-notifier\n\n# or cron (every 30 minutes)\n*/30 * * * * cd /path/to/signl && /path/to/signl/.venv/bin/python -m src.main --config ./config.yaml --once \\\n  >> /path/to/signl/signl.log 2>&1`}
                </code>
              </pre>
            </div>
          </div>
        </section>

        <section id="config" className="section">
          <div className="section-title">
            <p className="eyebrow">Config</p>
            <h2>Target what matters to your environment.</h2>
          </div>
          <div className="config-grid">
            <div className="config-column">
              <div className="panel">
                <h3>Example config.yaml</h3>
                <pre>
                  <code>{exampleConfig}</code>
                </pre>
              </div>
            </div>
            <div className="config-column">
              <div className="panel expected">
                <h3>What alerts look like</h3>
                <div className="alert-card">
                  <div className="alert-head">
                    <span className="alert-source">NVD</span>
                    <span className="alert-severity critical">P0 92</span>
                  </div>
                  <p className="alert-title">
                    CVE-2024-1890: Prototype pollution in lodash
                  </p>
                  <p className="alert-meta">Matched: direct dependency lodash</p>
                  <a className="alert-link" href="#" aria-label="Open advisory">
                    Read advisory →
                  </a>
                  <div className="alert-tags">
                    <span>Package</span>
                    <span>npm</span>
                    <span>Slack</span>
                  </div>
                </div>
                <div className="alert-card">
                  <div className="alert-head">
                    <span className="alert-source">GitHub</span>
                    <span className="alert-severity high">P2 58</span>
                  </div>
                  <p className="alert-title">
                    GHSA-xxxx-yyyy: Request handling bug in requests
                  </p>
                  <p className="alert-meta">Matched: transitive dependency requests</p>
                  <a className="alert-link" href="#" aria-label="Open advisory">
                    Read advisory →
                  </a>
                  <div className="alert-tags">
                    <span>Package</span>
                    <span>pip</span>
                    <span>Webhook</span>
                  </div>
                </div>
                <div className="alert-card">
                  <div className="alert-head">
                    <span className="alert-source">MSRC</span>
                    <span className="alert-severity medium">P3 35</span>
                  </div>
                  <p className="alert-title">
                    Azure advisory impacting Kubernetes control plane
                  </p>
                  <p className="alert-meta">Matched: service kubernetes</p>
                  <a className="alert-link" href="#" aria-label="Open advisory">
                    Read advisory →
                  </a>
                  <div className="alert-tags">
                    <span>Service</span>
                    <span>Azure</span>
                    <span>Discord</span>
                  </div>
                </div>
                <div className="alert-card">
                  <div className="alert-head">
                    <span className="alert-source">CISA</span>
                    <span className="alert-severity critical">P0 90</span>
                  </div>
                  <p className="alert-title">
                    KEV: RCE in widely used npm package
                  </p>
                  <p className="alert-meta">Matched: transitive dependency</p>
                  <a className="alert-link" href="#" aria-label="Open advisory">
                    Read advisory →
                  </a>
                  <div className="alert-tags">
                    <span>Package</span>
                    <span>npm</span>
                    <span>Slack</span>
                  </div>
                </div>
                <p className="note">
                  These are the kinds of alerts this config will send. Everything
                  else is ignored.
                </p>
              </div>
            </div>
          </div>
          <div className="panel config-note full-width">
            <h3>Match logic</h3>
            <ul className="list">
              <li>Direct dependency match (manifest or lockfile)</li>
              <li>Transitive dependency match (optional)</li>
              <li>Service or cloud match with synonyms</li>
              <li>Keyword or language context</li>
            </ul>
            <p className="note">
              Loose mode uses normalization + synonyms; strict mode requires exact matches.
            </p>
          </div>
        </section>

      <section className="section">
        <div className="section-title">
          <p className="eyebrow">Architecture</p>
          <h2>Lean by design.</h2>
        </div>
        <div className="arch">
            <div>
              <h3>Feeds</h3>
              <p>
                NVD, GitHub advisories, MSRC, CISA KEV, OSV, Hacker News, plus
                configurable RSS feeds.
              </p>
            </div>
            <div>
              <h3>Matcher</h3>
              <p>Dependency-aware matching with strict/loose modes and synonyms.</p>
            </div>
            <div>
              <h3>Notifier</h3>
              <p>Slack, Discord, or generic webhook with priority + rationale.</p>
            </div>
            <div>
              <h3>State</h3>
              <p>Local JSON store prevents duplicate alerts.</p>
            </div>
        </div>
      </section>

      <section className="section faq">
        <div className="section-title">
          <p className="eyebrow">FAQ</p>
          <h2>Quick answers for testing + setup.</h2>
        </div>
        <div className="faq-grid">
          <details className="faq-card">
            <summary>Why did nothing happen on dry run?</summary>
            <p>
              signl only prints when an item matches your stack. If there are no
              matches in the last 24 hours, you will see no output.
            </p>
          </details>
          <details className="faq-card">
            <summary>What is state.json and why does it matter?</summary>
            <p>
              signl stores the last poll time in <strong>state.json</strong>. If
              you are testing, delete it to re-scan the full 24-hour window.
            </p>
            <pre>
              <code>{`rm -f state.json`}</code>
            </pre>
          </details>
          <details className="faq-card">
            <summary>How do I verify my webhook works?</summary>
            <p>
              Run <strong>--test-notify</strong> to send a synthetic alert and
              confirm Slack or Discord delivery.
            </p>
            <pre>
              <code>{`python -m src.main --config ./config.yaml --test-notify`}</code>
            </pre>
          </details>
          <details className="faq-card">
            <summary>Pip says externally-managed-environment (PEP 668)</summary>
            <p>
              Use a virtual environment before installing dependencies to avoid
              system Python conflicts.
            </p>
            <pre>
              <code>
                {`python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt`}
              </code>
            </pre>
          </details>
          <details className="faq-card">
            <summary>GitHub rate limit hit</summary>
            <p>
              GitHub advisories are rate limited. Set <strong>GITHUB_TOKEN</strong>
              or disable the GitHub feed in config.
            </p>
          </details>
          <details className="faq-card">
            <summary>Can I disable specific feeds?</summary>
            <p>
              Yes. Set <strong>feeds.github</strong>, <strong>feeds.nvd</strong>,
              <strong>feeds.msrc</strong>, or nested <strong>enabled</strong> flags
              to false in <strong>config.yaml</strong>.
            </p>
          </details>
          <details className="faq-card">
            <summary>How do I avoid webhook rate limits?</summary>
            <p>
              Set <strong>settings.max_notifications_per_run</strong> to cap the
              number of alerts per run during testing.
            </p>
            <pre>
              <code>{`settings:\n  max_notifications_per_run: 10`}</code>
            </pre>
          </details>
          <details className="faq-card">
            <summary>Can I filter by severity?</summary>
            <p>
              Yes. Set <strong>settings.min_cvss_score</strong> to only alert on
              items at or above the score you choose.
            </p>
            <pre>
              <code>{`settings:\n  min_cvss_score: 7.0`}</code>
            </pre>
          </details>
          <details className="faq-card">
            <summary>How do I run this on a schedule (cron)?</summary>
            <p>
              Cron is a built-in scheduler. This runs signl every 30 minutes
              while your computer is on.
            </p>
            <pre>
              <code>
                {`crontab -e\n\n*/30 * * * * cd /path/to/signl && /path/to/signl/.venv/bin/python -m src.main --config ./config.yaml --once \\\n  >> /path/to/signl/signl.log 2>&1`}
              </code>
            </pre>
            <p>
              You will only get alerts when something matches. Logs are saved to{" "}
              <strong>signl.log</strong> in the repo folder.
            </p>
          </details>
          <details className="faq-card">
            <summary>No alerts showing up</summary>
            <p>
              Alerts only fire on matches. Add a broad keyword (like
              <strong> azure</strong>) for testing, then remove it later.
            </p>
          </details>
        </div>
      </section>
      </main>

      <footer className="footer">
        <p>Open-source, self-hosted, built for zero-noise security monitoring.</p>
        <p className="footer-note">
          Built for analysts by an analyst{" "}
          <a href="https://heyosj.com" target="_blank" rel="noreferrer">
            @heyosj
          </a>
          .
        </p>
      </footer>
    </>
  );
}
