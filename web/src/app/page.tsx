export default function Home() {
  const setupCommand = [
    "git clone https://github.com/heyosj/signl.git",
    "cd signl",
  ].join("\n");

  const envCommand = [
    "export DISCORD_WEBHOOK_URL=\"https://discord.com/api/webhooks/...\"",
    "# or",
    "export SLACK_WEBHOOK_URL=\"https://hooks.slack.com/services/...\"",
  ].join("\n");

  const exampleConfig = [
    "stack:",
    "  cloud:",
    "    - azure",
    "    - aws",
    "",
    "  packages:",
    "    npm:",
    "      - lodash",
    "    pip:",
    "      - requests",
    "",
    "  services:",
    "    - kubernetes",
    "    - redis",
    "",
    "notifications:",
    "  slack:",
    "    webhook_url: \"${SLACK_WEBHOOK_URL}\"",
    "  # discord:",
    "  #   webhook_url: \"${DISCORD_WEBHOOK_URL}\"",
    "",
    "settings:",
    "  poll_interval_minutes: 15",
    "  state_file: \"./state.json\"",
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
              Define your cloud, languages, packages, and services once. The
              notifier polls security feeds and sends you Slack alerts only when
              something actually applies to your environment.
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
              <span className="chip">Severity: Critical (9.8)</span>
              <span className="chip">Source: NVD</span>
            </div>
            <div className="reason">
              Why you are seeing this: Package match: lodash
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
              <p>List clouds, languages, packages, services, and keywords in YAML.</p>
            </div>
            <div className="step">
              <span className="step-number">02</span>
              <h3>Poll trusted feeds</h3>
              <p>NVD, GitHub advisories, and MSRC updates are checked on a schedule.</p>
            </div>
            <div className="step">
              <span className="step-number">03</span>
              <h3>Match and notify</h3>
              <p>Only items that match your stack are sent to Slack.</p>
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
              <p>
                For testing, add your stack + Discord webhook, then run once.
              </p>
              <pre>
                <code>
                  {`touch config.yaml\n${envCommand}\npython -m src.main --config ./config.yaml --once`}
                </code>
              </pre>
            </div>
            <div className="step-arrow" aria-hidden="true"></div>
            <div className="setup-step accent">
              <div className="setup-step-header">
                <span className="step-number">+</span>
                <h3>Production option</h3>
              </div>
              <p>Run in Docker and mount config/state for persistence.</p>
              <pre>
                <code>
                  {`docker run \\\n  -v ./config.yaml:/app/config.yaml \\\n  -v ./state.json:/app/state.json \\\n  security-stack-notifier`}
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
              <div className="panel config-note">
                <h3>Match logic</h3>
                <ul className="list">
                  <li>Direct package name match</li>
                  <li>Service name match</li>
                  <li>Keyword match</li>
                  <li>Language mention (contextual)</li>
                  <li>Cloud provider mention (contextual)</li>
                </ul>
                <p className="note">
                  Noisy matches are avoided with token-aware matching for short words.
                </p>
              </div>
            </div>
            <div className="panel expected">
              <h3>What alerts look like</h3>
              <div className="alert-card">
                <div className="alert-head">
                  <span className="alert-source">NVD</span>
                  <span className="alert-severity critical">Critical 9.8</span>
                </div>
                <p className="alert-title">
                  CVE-2024-1890: Prototype pollution in lodash
                </p>
                <p className="alert-meta">Matched: package lodash</p>
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
                  <span className="alert-severity high">High 7.5</span>
                </div>
                <p className="alert-title">
                  GHSA-xxxx-yyyy: Request handling bug in requests
                </p>
                <p className="alert-meta">Matched: package requests</p>
                <a className="alert-link" href="#" aria-label="Open advisory">
                  Read advisory →
                </a>
                <div className="alert-tags">
                  <span>Package</span>
                  <span>pip</span>
                  <span>Slack</span>
                </div>
              </div>
              <div className="alert-card">
                <div className="alert-head">
                  <span className="alert-source">MSRC</span>
                  <span className="alert-severity medium">Medium</span>
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
                  <span>Slack</span>
                </div>
              </div>
              <p className="note">
                These are the kinds of alerts this config will send. Everything
                else is ignored.
              </p>
            </div>
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
              <p>Prioritized relevance scoring using your stack definition.</p>
            </div>
            <div>
              <h3>Notifier</h3>
              <p>Slack or Discord webhooks with severity + reasons.</p>
            </div>
            <div>
              <h3>State</h3>
              <p>Local JSON store prevents duplicate alerts.</p>
            </div>
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
