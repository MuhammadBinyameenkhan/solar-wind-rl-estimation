"""Word (OMML) equations of the IEEE 33-bus manuscript (paper/make_ieee33_pwp.js), keyed 'B1', 'B2', ...

Each equation is written once in LaTeX; the forms follow the code in study3_ieee33/vsgrl33 and vsgrl/envs.
Output: paper/equations/omml_ieee33.json (read by insert_equations.py with its optional fourth argument).
Run: python paper/ieee33_equations.py   (needs pypandoc_binary, as make_equations.py)
"""
import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import pypandoc

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from make_equations import fix_omml  # noqa: E402

EQS = [
    ("B1", r"\mathbf{Y}\,\mathbf{V} = \mathbf{I}_{\mathrm{inj}}(\mathbf{V}) + \mathbf{I}_{E}\left(E'_q\angle\delta_d,\; E_v\angle\theta_v\right)"),
    ("B2", r"2H_d\,\frac{d\Delta\omega_d}{dt} = P_m - P_{e,d} - D_d\left(\Delta\omega_d - \Delta\omega_b\right), \qquad \frac{d\delta_d}{dt} = \omega_0\,\Delta\omega_d"),
    ("B3", r"T'_{do}\,\frac{dE'_q}{dt} = E_{fd} - E'_q - \left(X_d - X'_d\right) i_d, \qquad E_{fd} = f_{\mathrm{AC8C}}\left(V_{t,d},\, I_{fd}\right)"),
    ("B4", r"P_{\mathrm{ref}} = P_{d0} - \frac{\Delta f_m}{R} + x_{\mathrm{agc}}, \quad \frac{dx_{\mathrm{agc}}}{dt} = -K_i\,\Delta f_m, \quad T_g\frac{dP_{\mathrm{gov}}}{dt} = P_{\mathrm{ref}} - P_{\mathrm{gov}}, \quad T_e\frac{dP_m}{dt} = P_{\mathrm{gov}} - P_m"),
    ("B5", r"2H_v\,\frac{d\Delta\omega_v}{dt} = P_{\mathrm{set}} - P_v - D_v\,\Delta\omega_v, \qquad \frac{d\theta_v}{dt} = \omega_0\,\Delta\omega_v, \qquad \frac{dP_{\mathrm{set}}}{dt} = -K_{i,b}\,\Delta f_m"),
    ("B6", r"T_f\,\frac{dE_v}{dt} = V_{\mathrm{ref}} - m_Q\,\frac{Q_v}{S_{\mathrm{conv}}} - V_{t,v}"),
    ("B7", r"\Delta\omega_b = \frac{K_d\,\Delta\omega_d + K_s\,\Delta\omega_v}{K_d + K_s}, \qquad T_f\,\frac{d\Delta f_m}{dt} = \Delta\omega_b - \Delta f_m, \qquad \mathrm{RoCoF} = \frac{d\Delta f_m}{dt}"),
    ("B8", r"\Delta P_{\mathrm{res}} = -\frac{\left(\left|\Delta f_m\right| - f_{db}\right)_{+}\,\mathrm{sgn}\left(\Delta f_m\right)}{k_f}\,P_{\mathrm{np}}, \qquad \tau\,\frac{dP_s}{dt} = \Delta P_{\mathrm{res}} - P_s"),
    ("B9", r"H_v = \begin{cases} H_0 + a_1\left(\bar H - H_0\right), & a_1 \ge 0 \\ H_0 + a_1\left(H_0 - H_{\min}\right), & a_1 < 0 \end{cases}, \qquad a \in [-1, 1]^2"),
    ("B10", r"\bar D = \min\!\left(D_{\max},\; \frac{h}{\Delta f_{\mathrm{band}}}\right), \qquad \bar H = \min\!\left(H_{\max},\; \frac{h}{2\,\mathrm{RoCoF}_{\lim}}\right)"),
    ("B11", r"r_t = -\Big[w_f\,\overline{\left(|\Delta f| - f_{\mathrm{band}}\right)_{+}^{2}} + w_r\,\overline{\left(|\mathrm{RoCoF}| - r_{\mathrm{band}}\right)_{+}^{2}} + w_{\mathrm{fast}}\,\overline{\left(P_v - P_{\mathrm{set}}\right)^{2}} + w_b\,\overline{P_b^{2}} + w_s\,\overline{s} + w_v\,\nu + w_{\Delta}\left\|a_t - a_{t-1}\right\|^{2} + w_a\left\|a_t\right\|^{2}\Big]"),
    ("B12", r"G_{\mathrm{scen}} = \frac{\frac{1}{N}\sum_{n}\max_{g}R_{n,g} - \max_{g}\frac{1}{N}\sum_{n}R_{n,g}}{\left|\max_{g}\frac{1}{N}\sum_{n}R_{n,g}\right|}, \qquad G_{\mathrm{event}} = \frac{\frac{1}{N}\sum_{n}\max_{g_1,\dots,g_K}R_{n}(g_1,\dots,g_K) - \max_{g}\frac{1}{N}\sum_{n}R_{n,g}}{\left|\max_{g}\frac{1}{N}\sum_{n}R_{n,g}\right|}"),
    ("B13", r"\mathrm{gap\ closed} = \frac{R_{\pi} - R_{\mathrm{fix}}}{R_{\mathrm{oracle}} - R_{\mathrm{fix}}}"),
]


def doc_form(tex):
    if r"\qquad" in tex:
        return r"\begin{gathered} " + r" \\ ".join(p.strip() for p in tex.split(r"\qquad")) + r" \end{gathered}"
    return tex


if __name__ == "__main__":
    md = "\n\n".join(f"$$ {doc_form(t)} $$" for _, t in EQS)
    f = tempfile.mktemp(suffix=".docx")
    pypandoc.convert_text(md, "docx", format="markdown", outputfile=f)
    xml = zipfile.ZipFile(f).read("word/document.xml").decode("utf8")
    Path(f).unlink()
    paras = re.findall(r"<m:oMathPara>.*?</m:oMathPara>", fix_omml(xml), flags=re.S)
    assert len(paras) == len(EQS), (len(paras), len(EQS))
    out = HERE / "equations" / "omml_ieee33.json"
    out.write_text(json.dumps({k: p for (k, _), p in zip(EQS, paras)}, ensure_ascii=False, indent=0), encoding="utf8")
    print("wrote", len(paras), "equations to", out)
