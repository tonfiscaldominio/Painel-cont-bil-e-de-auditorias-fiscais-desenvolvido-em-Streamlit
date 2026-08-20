from __future__ import annotations

from io import BytesIO
from datetime import date
import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Painel Contábil e Fiscal", page_icon="📊", layout="wide")

REQUIRED_NOTE_COLUMNS = {
    "chave_nfe": "Chave NF-e",
    "data_emissao": "Data de emissão",
    "cnpj_emitente": "CNPJ emitente",
    "cnpj_destinatario": "CNPJ destinatário",
    "valor_total": "Valor total",
    "valor_icms": "Valor ICMS",
    "valor_pis": "Valor PIS",
    "valor_cofins": "Valor COFINS",
    "cfop": "CFOP",
    "status": "Status",
}

OBLIGATION_COLUMNS = {
    "obrigacao": "Obrigação",
    "periodo": "Período",
    "vencimento": "Vencimento",
    "entrega": "Data de entrega",
    "status": "Status",
    "valor_declarado": "Valor declarado",
}


def demo_notes() -> pd.DataFrame:
    rows = [
        ["35260812345678000199550010000000011000000010", "2026-01-05", "12.345.678/0001-99", "98.765.432/0001-11", 18500.00, 3330.00, 305.25, 1407.00, 5102, "Autorizada"],
        ["35260812345678000199550010000000021000000020", "2026-01-08", "12.345.678/0001-99", "98.765.432/0001-11", 7300.00, 1314.00, 120.45, 554.80, 5102, "Autorizada"],
        ["35260812345678000199550010000000021000000020", "2026-01-08", "12.345.678/0001-99", "98.765.432/0001-11", 7300.00, 1314.00, 120.45, 554.80, 5102, "Autorizada"],
        ["35260812345678000199550010000000031000000030", "2026-01-14", "45.111.222/0001-55", "12.345.678/0001-99", 42000.00, 7560.00, 693.00, 3192.00, 6108, "Autorizada"],
        ["35260812345678000199550010000000041000000040", "2026-02-02", "45.111.222/0001-55", "12.345.678/0001-99", 100.00, 0.00, 0.00, 0.00, 6108, "Cancelada"],
        ["35260812345678000199550010000000051000000050", "2026-02-18", "45.111.222/0001-55", "12.345.678/0001-99", 98000.00, 17640.00, 0.00, 0.00, 6108, "Autorizada"],
    ]
    return pd.DataFrame(rows, columns=list(REQUIRED_NOTE_COLUMNS))


def demo_obligations() -> pd.DataFrame:
    rows = [
        ["PGDAS-D", "2026-01", "2026-02-20", "2026-02-18", "Entregue", 12500.00],
        ["DCTFWeb", "2026-01", "2026-02-15", "", "Pendente", 0.00],
        ["EFD-Contribuições", "2026-01", "2026-03-10", "", "Em preparação", 0.00],
        ["GIA/ICMS", "2026-01", "2026-02-25", "2026-02-24", "Entregue", 9800.00],
        ["ECF", "2025", "2026-07-31", "", "Pendente", 0.00],
    ]
    return pd.DataFrame(rows, columns=list(OBLIGATION_COLUMNS))


def normalise_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    mapping = REQUIRED_NOTE_COLUMNS if kind == "notas" else OBLIGATION_COLUMNS
    aliases = {}
    for internal, label in mapping.items():
        aliases[internal.lower()] = internal
        aliases[label.lower()] = internal
        aliases[internal.replace("_", " ").lower()] = internal
    renamed = {}
    for col in df.columns:
        key = str(col).strip().lower()
        renamed[col] = aliases.get(key, key.replace(" ", "_").replace("-", "_"))
    out = df.rename(columns=renamed).copy()
    for col in mapping:
        if col not in out.columns:
            out[col] = pd.NA
    for col in ["data_emissao", "vencimento", "entrega"]:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    for col in ["valor_total", "valor_icms", "valor_pis", "valor_cofins", "valor_declarado"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)
    return out


def load_excel(uploaded) -> tuple[pd.DataFrame, pd.DataFrame]:
    sheets = pd.read_excel(uploaded, sheet_name=None)
    notes = []
    obligations = []
    for name, frame in sheets.items():
        normalized = normalise_columns(frame, "notas")
        score_notes = sum(col in frame.columns.str.lower().str.replace(" ", "_").tolist() for col in REQUIRED_NOTE_COLUMNS)
        if any(token in str(name).lower() for token in ["obrig", "fiscal", "declar"]):
            obligations.append(normalise_columns(frame, "obrigacoes"))
        elif score_notes >= 2 or any("nfe" in str(c).lower() or "nota" in str(c).lower() for c in frame.columns):
            notes.append(normalized)
        else:
            obligations.append(normalise_columns(frame, "obrigacoes"))
    notes_df = pd.concat(notes, ignore_index=True) if notes else pd.DataFrame(columns=list(REQUIRED_NOTE_COLUMNS))
    obligations_df = pd.concat(obligations, ignore_index=True) if obligations else pd.DataFrame(columns=list(OBLIGATION_COLUMNS))
    return notes_df, obligations_df


def detect_anomalies(notes: pd.DataFrame, obligations: pd.DataFrame) -> pd.DataFrame:
    findings = []
    if notes.empty:
        return pd.DataFrame(columns=["categoria", "severidade", "registro", "descricao", "valor"])
    work = notes.copy()
    for idx, row in work.iterrows():
        key = str(row.get("chave_nfe", ""))
        if key and key != "<NA>" and work["chave_nfe"].astype(str).duplicated(keep=False).iloc[idx]:
            findings.append(["Duplicidade", "Alta", idx + 1, "Chave NF-e repetida na base importada.", row.get("valor_total", 0)])
        total = float(row.get("valor_total", 0) or 0)
        icms = float(row.get("valor_icms", 0) or 0)
        if total < 0:
            findings.append(["Valor inválido", "Alta", idx + 1, "Documento com valor total negativo.", total])
        if total > 0 and icms > total:
            findings.append(["Imposto inconsistente", "Alta", idx + 1, "ICMS superior ao valor total do documento.", icms])
        if str(row.get("status", "")).lower() in {"cancelada", "cancelado"} and total > 0:
            findings.append(["Status fiscal", "Média", idx + 1, "Documento cancelado com valor econômico informado.", total])
    if not obligations.empty:
        today = pd.Timestamp.today().normalize()
        for idx, row in obligations.iterrows():
            due = row.get("vencimento")
            status = str(row.get("status", "")).lower()
            if pd.notna(due) and due < today and status not in {"entregue", "transmitida", "transmitido"}:
                findings.append(["Obrigação em atraso", "Alta", idx + 1, f"{row.get('obrigacao', 'Obrigação')} vencida sem entrega registrada.", row.get("valor_declarado", 0)])
    return pd.DataFrame(findings, columns=["categoria", "severidade", "registro", "descricao", "valor"])


def excel_download(df: pd.DataFrame, sheet_name: str) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return buffer.getvalue()


st.title("Painel Contábil e de Auditorias Fiscais")
st.caption("MVP para análise de obrigações, documentos fiscais e indícios de anomalia")

with st.sidebar:
    st.header("Configuração")
    regime = st.selectbox("Regime tributário", ["Simples Nacional", "Lucro Presumido", "Lucro Real"])
    competencia = st.date_input("Data de referência", value=date.today())
    uploaded = st.file_uploader("Importe um arquivo Excel", type=["xlsx", "xls"], help="Use abas para notas e obrigações. Os nomes das colunas podem estar em português ou nos nomes técnicos documentados.")
    usar_demo = st.checkbox("Usar dados demonstrativos", value=uploaded is None)

if uploaded is not None and not usar_demo:
    try:
        notes, obligations = load_excel(uploaded)
        st.success(f"Arquivo carregado: {uploaded.name}")
    except Exception as exc:
        st.error(f"Não foi possível ler o Excel: {exc}")
        notes, obligations = demo_notes(), demo_obligations()
else:
    notes, obligations = demo_notes(), demo_obligations()

notes = normalise_columns(notes, "notas")
obligations = normalise_columns(obligations, "obrigacoes")
anomalies = detect_anomalies(notes, obligations)

with st.sidebar:
    st.divider()
    st.metric("Notas carregadas", f"{len(notes):,}".replace(",", "."))
    st.metric("Obrigações", f"{len(obligations):,}".replace(",", "."))
    st.caption(f"Regime selecionado: {regime}")

if notes.empty and obligations.empty:
    st.warning("Importe um Excel com dados ou ative o modo demonstrativo para visualizar o painel.")
    st.stop()

# Filtros globais
with st.expander("Filtros da análise", expanded=True):
    c1, c2, c3 = st.columns(3)
    date_min = notes["data_emissao"].min() if notes["data_emissao"].notna().any() else pd.Timestamp("2000-01-01")
    date_max = notes["data_emissao"].max() if notes["data_emissao"].notna().any() else pd.Timestamp.today()
    period = c1.date_input("Período das notas", value=(date_min.date(), date_max.date()))
    status_filter = c2.multiselect("Status das notas", sorted(notes["status"].dropna().astype(str).unique()), default=sorted(notes["status"].dropna().astype(str).unique()))
    cfop_filter = c3.multiselect("CFOP", sorted(notes["cfop"].dropna().astype(str).unique()), default=sorted(notes["cfop"].dropna().astype(str).unique()))

filtered = notes.copy()
if isinstance(period, tuple) and len(period) == 2:
    filtered = filtered[(filtered["data_emissao"].dt.date >= period[0]) & (filtered["data_emissao"].dt.date <= period[1])]
if status_filter:
    filtered = filtered[filtered["status"].astype(str).isin(status_filter)]
if cfop_filter:
    filtered = filtered[filtered["cfop"].astype(str).isin(cfop_filter)]

# Abas do produto
summary, obligations_tab, cross, anomaly_tab, data_tab = st.tabs(["Visão geral", "Obrigações fiscais", "Cruzamentos de notas", "Anomalias", "Dados e exportação"])

with summary:
    st.subheader(f"Resumo gerencial — {regime}")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Valor das notas", f"R$ {filtered['valor_total'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    k2.metric("ICMS destacado", f"R$ {filtered['valor_icms'].sum():,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    k3.metric("Documentos autorizados", int((filtered["status"].astype(str).str.lower() == "autorizada").sum()))
    k4.metric("Achados de auditoria", len(anomalies))
    left, right = st.columns(2)
    with left:
        monthly = filtered.assign(mes=filtered["data_emissao"].dt.to_period("M").astype(str)).groupby("mes", as_index=False)["valor_total"].sum()
        st.plotly_chart(px.bar(monthly, x="mes", y="valor_total", title="Valor das notas por competência", labels={"mes": "Competência", "valor_total": "Valor (R$)"}), use_container_width=True)
    with right:
        status = filtered["status"].astype(str).value_counts().rename_axis("status").reset_index(name="quantidade")
        st.plotly_chart(px.pie(status, names="status", values="quantidade", title="Distribuição por status"), use_container_width=True)

with obligations_tab:
    st.subheader("Acompanhamento de obrigações")
    today = pd.Timestamp.today().normalize()
    obligations_view = obligations.copy()
    obligations_view["classificacao"] = obligations_view.apply(lambda r: "Entregue" if str(r["status"]).lower() in {"entregue", "transmitida", "transmitido"} else ("Em atraso" if pd.notna(r["vencimento"]) and r["vencimento"] < today else "Em aberto"), axis=1)
    a, b, c = st.columns(3)
    a.metric("Entregues", int((obligations_view["classificacao"] == "Entregue").sum()))
    b.metric("Em atraso", int((obligations_view["classificacao"] == "Em atraso").sum()))
    c.metric("Em aberto", int((obligations_view["classificacao"] == "Em aberto").sum()))
    st.dataframe(obligations_view, use_container_width=True, hide_index=True)

with cross:
    st.subheader("Cruzamentos e consistência documental")
    c1, c2 = st.columns(2)
    with c1:
        duplicate_keys = filtered[filtered["chave_nfe"].astype(str).duplicated(keep=False)].sort_values("chave_nfe")
        st.write("**Chaves NF-e duplicadas**")
        st.dataframe(duplicate_keys[["chave_nfe", "data_emissao", "valor_total", "status"]], use_container_width=True, hide_index=True)
    with c2:
        inconsistency = filtered[(filtered["valor_total"] > 0) & (filtered["valor_icms"] > filtered["valor_total"])]
        st.write("**Impostos superiores ao valor do documento**")
        st.dataframe(inconsistency[["chave_nfe", "valor_total", "valor_icms", "cfop"]], use_container_width=True, hide_index=True)
    st.info("O cruzamento usa a chave da NF-e, status, datas, CFOP e valores tributários. Regras específicas por regime devem ser validadas com o contador responsável antes de uso operacional.")

with anomaly_tab:
    st.subheader("Fila de achados para auditoria")
    if anomalies.empty:
        st.success("Nenhuma anomalia foi identificada pelas regras atuais.")
    else:
        sev = st.multiselect("Filtrar severidade", sorted(anomalies["severidade"].unique()), default=sorted(anomalies["severidade"].unique()))
        st.dataframe(anomalies[anomalies["severidade"].isin(sev)], use_container_width=True, hide_index=True)
        st.download_button("Baixar achados em Excel", excel_download(anomalies, "achados"), "achados_auditoria.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with data_tab:
    st.subheader("Dados importados e exportação")
    st.write("Abaixo estão as bases normalizadas utilizadas pelos indicadores e pelas regras de auditoria.")
    st.write("**Notas fiscais**")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("Baixar notas filtradas em Excel", excel_download(filtered, "notas"), "notas_filtradas.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.write("**Modelo de colunas aceitas**")
    st.code("chave_nfe, data_emissao, cnpj_emitente, cnpj_destinatario, valor_total, valor_icms, valor_pis, valor_cofins, cfop, status\nobrigacao, periodo, vencimento, entrega, status, valor_declarado", language="text")

st.divider()
st.caption("Painel demonstrativo. As regras tributárias e os prazos devem ser parametrizados e revisados conforme a legislação aplicável, o estado e o regime da empresa.")
