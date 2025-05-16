import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime, timedelta
import os

# Configurações do app
st.set_page_config(page_title="Dashboard eZSend One", layout="wide")
st.title("📊 Dashboard eZSend One")

# Sidebar para abas e datas
aba = st.sidebar.radio("Escolha o Relatório:", ["Relatório Geral", "Relatório por Cliente", "Eventos Detalhados"])

start_date = st.sidebar.date_input("Data Início", datetime.now() - timedelta(days=1))
end_date = st.sidebar.date_input("Data Fim", datetime.now())

start_str = start_date.strftime("%d/%m/%Y")
end_str = end_date.strftime("%d/%m/%Y")

# Configs da API
API_URL_GERAL = f"https://api.ezsend-one.eteg.app/events/internal/reports?startDate={start_str}&endDate={end_str}"
API_URL_DETALHADO = f"https://api.ezsend-one.eteg.app/events/internal/reports?clientId={{client_id}}&startDate={start_str}&endDate={end_str}"

HEADERS = {"x-api-key": os.environ.get("x-api-key")}

# Função para obter dados gerais
def get_dados_gerais():
    try:
        r = requests.get(API_URL_GERAL, headers=HEADERS)
        r.raise_for_status()
        return r.json()["results"]
    except Exception as e:
        st.error(f"Erro ao buscar dados gerais: {e}")
        return []

# Função para obter dados detalhados por clientId
def get_dados_detalhados(client_id):
    try:
        url = API_URL_DETALHADO.format(client_id=client_id)
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        return r.json()["results"]
    except Exception as e:
        st.error(f"Erro ao buscar eventos detalhados: {e}")
        return []

# ---- ABA 1: RELATÓRIO GERAL ----
if aba == "Relatório Geral":
    dados = get_dados_gerais()
    rows = []
    for item in dados:
        if "events" in item and "notification:sent:success" in item["events"]:
            rows.append({
                "Cliente": item["subdomain"],
                "Client ID": item["clientId"],
                "Enviadas ao Canal": item["events"].get("notification:delivery:channel", 0),
                "Falha na Entrega": item["events"].get("notification:delivery:failure", 0),
                "Entregues ao Usuário": item["events"].get("notification:delivery:user", 0),
                "Envio com Sucesso": item["events"].get("notification:sent:success", 0),
                "Falha no Envio": item["events"].get("notification:sent:failure", 0)
            })

    df = pd.DataFrame(rows).sort_values(by="Envio com Sucesso", ascending=False)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Enviadas", df["Enviadas ao Canal"].sum())
    col2.metric("Total Entregues", df["Entregues ao Usuário"].sum())
    col3.metric("Falhas de Envio", df["Falha no Envio"].sum())
    col4.metric("Falhas na Entrega", df["Falha na Entrega"].sum())

    st.markdown("---")
    st.subheader("📈 Envio com Sucesso por Cliente")
    fig = px.bar(df, x="Cliente", y="Envio com Sucesso", color="Cliente", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Dados Detalhados")
    st.dataframe(df, use_container_width=True)

# ---- ABA 2: RELATÓRIO POR CLIENTE ----
elif aba == "Relatório por Cliente":
    dados = get_dados_gerais()
    options = [item["subdomain"] for item in dados]
    subdomain = st.selectbox("Buscar Cliente (subdomain):", options)

    cliente = next((item for item in dados if item["subdomain"] == subdomain), None)
    if cliente:
        e = cliente["events"]
        st.metric("Enviadas", e.get("notification:delivery:channel", 0))
        st.metric("Entregues", e.get("notification:delivery:user", 0))
        st.metric("Falha Envio", e.get("notification:sent:failure", 0))
        st.metric("Falha Entrega", e.get("notification:delivery:failure", 0))

        df_cliente = pd.DataFrame([{
            "Categoria": "Enviadas ao Canal",
            "Quantidade": e.get("notification:delivery:channel", 0)
        },{
            "Categoria": "Entregues ao Usuário",
            "Quantidade": e.get("notification:delivery:user", 0)
        },{
            "Categoria": "Falha na Entrega",
            "Quantidade": e.get("notification:delivery:failure", 0)
        },{
            "Categoria": "Falha no Envio",
            "Quantidade": e.get("notification:sent:failure", 0)
        },{
            "Categoria": "Envio com Sucesso",
            "Quantidade": e.get("notification:sent:success", 0)
        }])

        fig_cliente = px.bar(df_cliente, x="Categoria", y="Quantidade", color="Categoria", text_auto=True)
        st.plotly_chart(fig_cliente, use_container_width=True)
        st.dataframe(df_cliente)

# ---- ABA 3: EVENTOS DETALHADOS ----
elif aba == "Eventos Detalhados":
    dados = get_dados_gerais()
    options = [item["subdomain"] for item in dados]
    subdomain = st.selectbox("Escolha o Cliente:", options)

    cliente = next((item for item in dados if item["subdomain"] == subdomain), None)
    if cliente:
        detalhes = get_dados_detalhados(cliente["clientId"])
        if detalhes:
            for d in detalhes:
                d["erro"] = d.get("error") is not None
            df_detalhes = pd.DataFrame(detalhes)
            colunas_exibir = [
                "notificationId", "whatsappTemplateName", "trigger", "createdAt", "erro"
            ]
            df_detalhes = df_detalhes[colunas_exibir] if all(c in df_detalhes.columns for c in colunas_exibir) else df_detalhes
            st.dataframe(df_detalhes, use_container_width=True)
        else:
            st.warning("Nenhum dado detalhado encontrado.")
