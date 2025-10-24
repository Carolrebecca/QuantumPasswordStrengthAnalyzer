# main.py
# Quantum Password Strength Analyzer (pure simulation + graph)
import streamlit as st
import math
import string
import secrets
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Quantum Password Strength Analyzer", layout="centered")

# ---------- Styling ----------
st.markdown(
    """
    <style>
    body { background-color: #0b0b0b; color: #eaeaea; font-family: Inter, sans-serif; }
    div.stButton > button {
        background: linear-gradient(90deg,#6b0f0f,#3d0a0a);
        color: white;
        border-radius:8px;
        padding:8px 12px;
        border:none;
    }
    .card { background: linear-gradient(180deg, rgba(20,20,20,0.95), rgba(12,12,12,0.75));
            padding:12px; border-radius:10px; border:1px solid rgba(140,40,40,0.12); }
    .small { font-size:13px; color:#cfcfcf; }
    .meter { width:100%; height:14px; background: rgba(255,255,255,0.04);
             border-radius:8px; overflow:hidden; margin-top:6px; }
    .meter > .fill { height:100%; background: linear-gradient(90deg,#8b1a1a,#b83b3b);
                     width:0%; transition: width 0.6s ease; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<div class='card'><h2>🔐 Quantum Password Strength Analyzer</h2>"
    "<div class='small'>Compare classical vs quantum (Grover) brute-force resistance</div></div>",
    unsafe_allow_html=True,
)

# ---------- Utilities ----------
POOL_SIZES = {"lower": 26, "upper": 26, "digits": 10, "symbols": 32}

def estimate_entropy(password: str) -> float:
    pool = 0
    if any(c.islower() for c in password): pool += POOL_SIZES["lower"]
    if any(c.isupper() for c in password): pool += POOL_SIZES["upper"]
    if any(c.isdigit() for c in password): pool += POOL_SIZES["digits"]
    if any(c in string.punctuation for c in password): pool += POOL_SIZES["symbols"]
    if pool == 0:
        return 0.0
    return round(math.log2(pool) * len(password), 2)

def human_time(seconds: float) -> str:
    if seconds != seconds or seconds == float("inf"):
        return "∞"
    if seconds < 1:
        return f"{seconds:.3f} s"
    minute, hour, day, year = 60, 3600, 86400, 31536000
    if seconds < minute:
        return f"{seconds:.2f} s"
    if seconds < hour:
        return f"{seconds/minute:.2f} min"
    if seconds < day:
        return f"{seconds/hour:.2f} hr"
    if seconds < year:
        return f"{seconds/day:.2f} days"
    return f"{seconds/year:.2f} years"

def classical_time_seconds(entropy_bits, ops_per_sec, average=True):
    if ops_per_sec <= 0:
        return float("inf")
    full = 2**entropy_bits / ops_per_sec
    return full/2 if average else full

def grover_time_seconds(entropy_bits, quantum_ops_per_sec, average=True):
    if quantum_ops_per_sec <= 0:
        return float("inf")
    full = 2**(entropy_bits/2) / quantum_ops_per_sec
    return full/2 if average else full

def time_to_percent_years(seconds: float) -> int:
    if seconds <= 1:
        return 0
    years = seconds / (3600*24*365)
    if years >= 100:
        return 100
    pct = int((math.log10(years + 1) / 2.0) * 100)
    return max(0, min(100, pct))

# ---------- Input ----------
st.subheader("Input")

if "password" not in st.session_state:
    st.session_state["password"] = ""

col1, col2 = st.columns([3, 1])
with col1:
    password = st.text_input("Password to analyze", value=st.session_state["password"])
with col2:
    gen_len = st.number_input("Generate length", min_value=6, max_value=64, value=12, step=1)
    if st.button("Generate random password"):
        alphabet = string.ascii_letters + string.digits + string.punctuation
        st.session_state["password"] = "".join(secrets.choice(alphabet) for _ in range(gen_len))
        st.rerun()

password = st.session_state["password"]

st.write("")
st.subheader("Attacker assumptions")
c_ops = st.number_input("Classical guesses/sec", value=1e9, format="%.0f")
q_ops = st.number_input("Quantum ops/sec (Grover oracle)", value=1e6, format="%.0f")

# ---------- Analysis ----------
if not password:
    st.info("Enter or generate a password to analyze.")
else:
    entropy = estimate_entropy(password)
    st.markdown(f"### Results for: `{password}`")
    st.markdown(f"**Estimated entropy:** **{entropy} bits**")

    classical_avg = classical_time_seconds(entropy, c_ops, average=True)
    quantum_avg = grover_time_seconds(entropy, q_ops, average=True)

    st.subheader("Estimated attack times")
    st.table([
        {"Scenario": "Classical (avg)", "Human time": human_time(classical_avg), "Seconds": f"{classical_avg:.3e}"},
        {"Scenario": "Quantum (avg)", "Human time": human_time(quantum_avg), "Seconds": f"{quantum_avg:.3e}"}
    ])

    st.subheader("Visual safety meters")
    c_pct = time_to_percent_years(classical_avg)
    q_pct = time_to_percent_years(quantum_avg)

    st.markdown("**Classical resistance**")
    st.markdown(f"<div class='meter'><div class='fill' style='width:{c_pct}%;'></div></div>", unsafe_allow_html=True)
    st.caption(f"≈ {human_time(classical_avg)} average")

    st.markdown("**Quantum resistance (Grover)**")
    st.markdown(f"<div class='meter'><div class='fill' style='width:{q_pct}%;'></div></div>", unsafe_allow_html=True)
    st.caption(f"≈ {human_time(quantum_avg)} average")

    st.subheader("Recommendations")
    if entropy < 40:
        st.error("Weak — use more diverse characters and longer length (≥12).")
    elif entropy < 60:
        st.warning("Moderate — okay but can be stronger with length ≥16.")
    elif entropy < 80:
        st.success("Strong — safe against classical and moderately safe against quantum attacks.")
    else:
        st.success("Very strong — high entropy; even Grover's algorithm struggles here.")

    st.markdown("---")

    # ---------- Graph ----------
    st.subheader("📊 Password Length vs Quantum & Classical Crack Time")

    # Simulate lengths 4–32 for same character pool as user's password
    lengths = list(range(4, 33))
    pool = 0
    if any(c.islower() for c in password): pool += POOL_SIZES["lower"]
    if any(c.isupper() for c in password): pool += POOL_SIZES["upper"]
    if any(c.isdigit() for c in password): pool += POOL_SIZES["digits"]
    if any(c in string.punctuation for c in password): pool += POOL_SIZES["symbols"]
    if pool == 0:
        pool = POOL_SIZES["lower"]

    data = []
    for l in lengths:
        e = math.log2(pool) * l
        c_t = classical_time_seconds(e, c_ops, True)
        q_t = grover_time_seconds(e, q_ops, True)
        data.append((l, e, math.log10(c_t+1), math.log10(q_t+1)))

    df = pd.DataFrame(data, columns=["Length", "Entropy (bits)", "log10(Classical sec)", "log10(Quantum sec)"])

    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(df["Length"], df["Entropy (bits)"], "o-", color="gold", label="Entropy (bits)")
    ax2 = ax1.twinx()
    ax2.plot(df["Length"], df["log10(Classical sec)"], "r--", label="Classical time (log10 s)")
    ax2.plot(df["Length"], df["log10(Quantum sec)"], "c--", label="Quantum time (log10 s)")

    ax1.set_xlabel("Password Length")
    ax1.set_ylabel("Entropy (bits)", color="gold")
    ax2.set_ylabel("log₁₀(Time in seconds)", color="white")
    ax1.grid(True, alpha=0.3)
    fig.patch.set_facecolor("#0b0b0b")
    ax1.set_facecolor("#0b0b0b")
    ax2.set_facecolor("#0b0b0b")
    ax1.tick_params(colors="white")
    ax2.tick_params(colors="white")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    st.pyplot(fig)

    st.caption("Entropy and attack times scale exponentially with length — Grover’s algorithm still provides only a √N speedup, so longer passwords remain secure.")

    st.markdown("---")
    st.caption("Note: This is a simulation. Real password security also depends on hashing algorithms (bcrypt, Argon2), salts, and system implementation.")
