/* ============ Technology News Agent — app ============ */
const { useState, useEffect, useRef, useCallback } = React;

/* ---------- tiny inline icons (simple strokes only) ---------- */
const Ico = {
  arrow: (p) => (<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M5 12h14M13 6l6 6-6 6"/></svg>),
  check: (p) => (<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 12.5l5 5L20 6.5"/></svg>),
  scan: (p) => (<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M4 7V5a1 1 0 0 1 1-1h2M17 4h2a1 1 0 0 1 1 1v2M20 17v2a1 1 0 0 1-1 1h-2M7 20H5a1 1 0 0 1-1-1v-2"/><path d="M4 12h16"/></svg>),
  spark: (p) => (<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M18 6l-2.5 2.5M8.5 15.5L6 18"/></svg>),
  inbox: (p) => (<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M3 12l3-7h12l3 7v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/><path d="M3 12h5l1.5 2.5h5L16 12h5"/></svg>),
  globe: (p) => (<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.7" {...p}><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 2.5 15 0 18M12 3c-2.5 2.5-2.5 15 0 18"/></svg>),
  link: (p) => (<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}><path d="M9 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-1.5 1.5M14 11a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l1.5-1.5"/></svg>),
};

const SOURCES = ["TechCrunch", "The Verge", "Ars Technica", "Hacker News", "WIRED", "MIT Tech Review", "The Information", "Bloomberg Tech", "Stratechery"];

const BRIEF = [
  { rank: "1.", cat: "Research", title: "Entanglement and Magic Build Space-Time Gravity",
    body: "Physicists trace the pliability of space-time to its quantum roots through a measure called \u2018magic\u2019 in holographic theories \u2014 a potential explanation for how gravity emerges from entanglement." },
  { rank: "2.", cat: "Research", title: "Russian Satellites Identified as Source of GNSS Interference",
    body: "A new paper attributes transient GNSS interference across Europe, Greenland and Canada since 2019 to a constellation of Russian early-warning satellites in Molniya orbits." },
  { rank: "3.", cat: "Tools", title: "ESP32-Bit-Pirate: Multi-Protocol Hardware Hacking Tool",
    body: "Open-source firmware that turns an ESP32 into a Bus-Pirate-style multi-protocol tool \u2014 sniff and script I2C, UART, SPI, Bluetooth and Wi-Fi from a serial or web CLI, with a one-click web flasher." },
];

/* ---------- Signup form ---------- */
function Signup({ id, compact }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [touched, setTouched] = useState({});
  const [done, setDone] = useState(false);
  const [num, setNum] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const nameOk = name.trim().length >= 2;
  const showNameErr = touched.name && !nameOk;
  const showEmailErr = touched.email && !emailOk;

  const submit = async (e) => {
    e.preventDefault();
    setTouched({ name: true, email: true });
    if (!nameOk || !emailOk) return;

    setLoading(true);
    setError(null);

    try {
      const res = await fetch ("/subscribe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), email: email.trim()}),
      });

      if(!res.ok){
        const data = await res.json();
        throw new Error(data.detail || "Something went wrong - try again.");
      }
      setNum(12400 + Math.floor(Math.random() * 90) + 11);
      setDone(true);
    } catch(err){
      setError(err.message);
    } finally {
      setLoading(false);
    }

  };

  if (done) {
    return (
      <div className="success" role="status">
        <div className="check">{Ico.check()}</div>
        <h3>You're on the list, {name.trim().split(" ")[0]}.</h3>
        <p>Your first brief lands <b style={{color:"var(--text)"}}>tomorrow at 9:00 AM</b>. Check {email.trim()} to confirm — it takes one tap.</p>
        <span className="badge">◆ subscriber #{num.toLocaleString()}</span>
      </div>
    );
  }

  return (
    <form className="signup" onSubmit={submit} noValidate>
      <div className="field-row">
        <div className={"field" + (showNameErr ? " invalid" : "")}>
          <input id={id+"-name"} type="text" placeholder="First name" value={name}
            autoComplete="given-name"
            onChange={(e)=>setName(e.target.value)}
            onBlur={()=>setTouched(t=>({...t,name:true}))} />
          {showNameErr && <div className="field-err">enter your name</div>}
        </div>
        <div className={"field" + (showEmailErr ? " invalid" : "")}>
          <input id={id+"-email"} type="email" placeholder="you@company.com" value={email}
            autoComplete="email"
            onChange={(e)=>setEmail(e.target.value)}
            onBlur={()=>setTouched(t=>({...t,email:true}))} />
          {showEmailErr && <div className="field-err">enter a valid email</div>}
        </div>
      </div>
      {error && (
        <div style={{color: "var(--danger, #f87171)", fontSize: "13px", marginBottom: "8px"}}>
          {error}
        </div>
      )}
      <button className="btn btn-primary" type="submit">
        Get my morning brief {Ico.arrow()}
      </button>
      <div className="signup-meta">
        <div className="avatars"><span></span><span></span><span></span><span></span></div>
        <span>Join <b>12,400+</b> engineers · free forever · no spam</span>
      </div>
    </form>
  );
}

/* ---------- Hero preview (animated sample brief) ---------- */
function Preview() {
  return (
    <div className="preview reveal">
      <div className="preview-head">
        <div className="dots"><i></i><i></i><i></i></div>
        <span className="tab">inbox — today's brief</span>
      </div>
      <div className="preview-body">
        <div className="mail-meta">
          <div className="mail-from">
            <div className="ic"><img src={(window.__resources&&window.__resources.mark)||"mark.svg"} alt="" style={{width:"90%",height:"90%"}} /></div>
            <div>
              <div className="n">Technology News Agent</div>
              <div className="e">agent@technews.ai</div>
            </div>
          </div>
          <div className="mail-date">FRI · JUN 5<br/>9:00 AM</div>
        </div>
        <div className="mail-subject"><span className="globe">{Ico.globe()}</span>Executive Technology News Briefing</div>
        <div className="rule"></div>
        <div className="tldr">Today’s briefing covers <b>9 stories</b> worth your attention.</div>
        {BRIEF.map((b, i) => (
          <div className="brief-item" key={b.rank} style={{ animationDelay: (0.4 + i * 0.25) + "s" }}>
            <span className="brief-cat">{b.cat}</span>
            <h4><span className="rank">{b.rank}</span> {b.title}</h4>
            <p>{b.body}</p>
            <a className="read-src" href="#subscribe" onClick={(e)=>e.preventDefault()}>{Ico.link()} Read Full Source</a>
          </div>
        ))}
        <div className="brief-more">
          <span>summarized from 52 sources overnight</span>
          <a href="#subscribe" onClick={(e)=>e.preventDefault()}>+ 6 more →</a>
        </div>
      </div>
    </div>
  );
}

/* ---------- Scroll reveal hook ---------- */
function useReveal() {
  useEffect(() => {
    const els = document.querySelectorAll(".reveal");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } });
    }, { threshold: 0.12 });
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
}

/* ---------- App ---------- */
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme": "dark"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", t.theme === "light" ? "light" : "dark");
  }, [t.theme]);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useReveal();

  return (
    <div className="shell">
      <div className="bg-field" aria-hidden="true">
        <div className="bg-grid"></div>
        <div className="bg-glow g1"></div>
        <div className="bg-glow g2"></div>
      </div>

      <nav className={"nav" + (scrolled ? " scrolled" : "")}>
        <div className="wrap nav-inner">
          <div className="brand">
            <div className="brand-mark"><img src={(window.__resources&&window.__resources.mark)||"mark.svg"} alt="Technology News Agent" /></div>
            <div className="brand-name">Technology <b>News</b></div>
          </div>
          <div className="nav-actions">
            <a className="nav-link" href="#how">How it works</a>
            <a className="nav-link" href="#sample">Sample brief</a>
            <a className="btn btn-ghost btn-sm" href="#subscribe">Subscribe</a>
          </div>
        </div>
      </nav>

      {/* HERO */}
      <header className="hero" id="subscribe">
        <div className="wrap hero-grid">
          <div>
            <span className="eyebrow"><span className="live"></span>Tech news agent · every weekday · 9:00 AM</span>
            <h1 className="headline">Stop scrolling tech news. <span className="hl">Let an agent read it</span> for you.</h1>
            <p className="subhead">Your AI agent reads 50+ sources overnight and sends one sharp, 5-minute brief of what actually matters — built for engineers who don't have time for noise.</p>
            <Signup id="hero" />
          </div>
          <Preview />
        </div>
      </header>

      {/* LOGOS */}
      <section className="logos">
        <div className="wrap">
          <p className="logos-label">Your agent reads — so you don't have to</p>
          <div className="logos-track reveal">
            {SOURCES.map((s) => <span className="logo-word" key={s}>{s}</span>)}
          </div>
        </div>
      </section>

      {/* HOW IT WORKS */}
      <section className="section" id="how">
        <div className="wrap">
          <p className="section-eyebrow reveal">// how the agent works</p>
          <h2 className="section-title reveal">Three steps. Zero effort from you.</h2>
          <p className="section-sub reveal">It runs every night while you sleep. You just open your inbox.</p>
          <div className="steps">
            {[
              { n:"step 01", ic: Ico.scan, h:"It scans the web", p:"Every night the agent crawls 50+ trusted tech sources — news sites, engineering blogs, research drops and release notes." },
              { n:"step 02", ic: Ico.spark, h:"It summarizes the signal", p:"It ranks stories by what matters to builders, strips the fluff, and writes plain-English summaries you can scan in seconds." },
              { n:"step 03", ic: Ico.inbox, h:"It lands in your inbox", p:"One clean email at 9:00 AM, every weekday. A 5-minute read that keeps you ahead — no app, no feed, no doom-scroll." },
            ].map((s,i)=>(
              <div className="step reveal" key={i} style={{transitionDelay:(i*0.08)+"s"}}>
                <div className="step-num">{s.n}</div>
                <div className="step-ic">{s.ic()}</div>
                <h3>{s.h}</h3>
                <p>{s.p}</p>
              </div>
            ))}
          </div>

          {/* STATS */}
          <div className="stats reveal">
            <div className="stat"><div className="num">12,400+</div><div className="lbl">readers</div></div>
            <div className="stat"><div className="num">50+</div><div className="lbl">sources scanned</div></div>
            <div className="stat"><div className="num">5 min</div><div className="lbl">to read</div></div>
            <div className="stat"><div className="num">0</div><div className="lbl">spam, ever</div></div>
          </div>
        </div>
      </section>

      {/* SAMPLE */}
      <section className="section" id="sample" style={{paddingTop:0}}>
        <div className="wrap">
          <p className="section-eyebrow reveal">// see it for yourself</p>
          <h2 className="section-title reveal">This is a real brief.</h2>
          <p className="section-sub reveal">No clickbait, no 800-word think-pieces. Ranked, summarized, sourced — here's exactly what tomorrow morning looks like.</p>
          <div style={{maxWidth:560, margin:"48px auto 0"}}>
            <Preview />
          </div>
        </div>
      </section>

      {/* FINAL CTA */}
      <section className="section" style={{paddingTop:0}}>
        <div className="wrap">
          <div className="cta-band reveal">
            <p className="section-eyebrow">// 12,400+ engineers already read it</p>
            <h2 className="section-title" style={{marginTop:12}}>Get tomorrow's brief.</h2>
            <p className="section-sub" style={{marginBottom:8}}>Free forever. One email each weekday. Unsubscribe in one click.</p>
            <Signup id="cta" />
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="footer">
        <div className="wrap footer-inner">
          <div className="brand">
            <div className="brand-mark"><img src={(window.__resources&&window.__resources.mark)||"mark.svg"} alt="Technology News Agent" /></div>
            <div className="brand-name">Technology <b>News</b></div>
          </div>
          <div className="footer-links">
            <a href="#how">How it works</a>
            <a href="#sample">Sample brief</a>
            <a href="#subscribe">Subscribe</a>
            <a href="#">Privacy</a>
          </div>
          <div className="copy">© 2026 By <a href="https://www.linkedin.com/in/abdalrahman-al-mahrouq-38a54b267/" style={{color:"inherit"}} target="_blank"> Abdalrahman Almahrouq </a> </div>
        </div>
      </footer>

      <TweaksPanel>
        <TweakSection label="Appearance" />
        <TweakRadio label="Theme" value={t.theme} options={["dark","light"]}
          onChange={(v)=>setTweak("theme", v)} />
      </TweaksPanel>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
