import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px

# Configuração da página estilo Investidor10
st.set_page_config(page_title="Meu Investidor 10", page_icon="📊", layout="wide")

# 🔗 CONFIGURAÇÃO DO BANCO DE DADOS (GOOGLE SHEETS)
# Substitua pelo link real da sua planilha configurada como "Editor"
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1_2adoWIAqFwFbEpwZfWJo3B6PiVzS6KPlQoPMoEcuK0/edit?usp=sharing"

# Trata o URL para ler como formato CSV direto do Google
if "edit?usp=sharing" in URL_PLANILHA:
    url_csv = URL_PLANILHA.replace("edit?usp=sharing", "gviz/tq?tqx=out:csv&sheet=Transacoes")
elif "edit#" in URL_PLANILHA:
    url_csv = URL_PLANILHA.split("edit#")[0] + "gviz/tq?tqx=out:csv&sheet=Transacoes"
else:
    url_csv = URL_PLANILHA + "/gviz/tq?tqx=out:csv&sheet=Transacoes"

st.title("📊 Dashboard de Controle de Investimentos")
st.subheader("Gerencie sua carteira de Ações e FIIs em tempo real")

# Função para carregar dados salvos na planilha
def carregar_dados():
    try:
        df = pd.read_csv(url_csv)
        # Garante que as colunas tenham os formatos certos
        df['Quantidade'] = pd.to_numeric(df['Quantidade'])
        df['Preço Unitário'] = pd.to_numeric(df['Preço Unitário'])
        return df
    except:
        return pd.DataFrame(columns=['Ticker', 'Quantidade', 'Preço Unitário', 'Tipo'])

# Função para salvar nova linha na planilha via requisição web simplificada
def salvar_na_planilha(ticker, qtd, preco, tipo):
    # Transforma o link normal em link de formulário de script ou usa o pandas se local
    # Como o streamlit cloud roda isolado, a forma mais robusta de salvar sem API paga é usar append local
    # Para fins de demonstração robusta, mantemos a leitura em tempo real.
    pass

# Inicializar/Carregar dados vindos da nuvem
if 'transacoes' not in st.session_state:
    st.session_state.transacoes = carregar_dados()

# --- ABA 1: LANÇAR INVESTIMENTOS ---
st.sidebar.header("➕ Nova Transação")
with st.sidebar.form(key='form_transacao', clear_on_submit=True):
    ticker = st.text_input("Ticker do Ativo (ex: PETR4,11 ou MXRF11)").upper().strip()
    if ticker and not ticker.endswith('.SA'):
        ticker_yf = f"{ticker}.SA"
    else:
        ticker_yf = ticker

    quantidade = st.number_input("Quantidade", min_value=1, step=1)
    preco = st.number_input("Preço Unitário (R$)", min_value=0.01, step=0.01, format="%.2f")
    tipo = st.selectbox("Tipo de Operação", ["Compra", "Venda"])
    
    botao_enviar = st.form_submit_button("Registrar Transação")

if botao_enviar and ticker:
    nova_linha = pd.DataFrame([{
        'Ticker': ticker_yf, 
        'Quantidade': quantidade if tipo == "Compra" else -quantidade, 
        'Preço Unitário': preco, 
        'Tipo': tipo
    }])
    st.session_state.transacoes = pd.concat([st.session_state.transacoes, nova_linha], ignore_index=True)
    
    # IMPORTANTE: Para o Streamlit Cloud salvar de verdade no Google Sheets sem travar,
    # a forma ideal de produção usa as "st.secrets". 
    # Para este protótipo, os dados ficam retidos na sessão atual enquanto você usa.
    st.sidebar.success(f"{tipo} de {ticker} registrada temporariamente!")

# --- LÓGICA DE CÁLCULO DA CARTEIRA ---
df_t = st.session_state.transacoes

if not df_t.empty:
    carteira = []
    for ticker_atual in df_t['Ticker'].unique():
        sub_df = df_t[df_t['Ticker'] == ticker_atual]
        qtd_total = sub_df['Quantidade'].sum()
        
        compras = sub_df[sub_df['Tipo'] == 'Compra']
        if not compras.empty and qtd_total > 0:
            preco_medio = (compras['Quantidade'] * compras['Preço Unitário']).sum() / compras['Quantidade'].sum()
            
            try:
                ticker_info = yf.Ticker(ticker_atual)
                preco_atual = ticker_info.history(period="1d")['Close'].iloc[-1]
            except:
                preco_atual = preco_medio
                
            valor_investido = qtd_total * preco_medio
            valor_atual = qtd_total * preco_atual
            lucro_prejuizo = valor_atual - valor_investido
            rentabilidade = (lucro_prejuizo / valor_investido) * 100 if valor_investido > 0 else 0
            
            classe = "FII" if "11" in ticker_atual else "Ação"
            
            carteira.append({
                'Ativo': ticker_atual.replace('.SA', ''),
                'Classe': classe,
                'Qtd': qtd_total,
                'Preço Médio': preco_medio,
                'Preço Atual': preco_atual,
                'Total Investido': valor_investido,
                'Total Atual': valor_atual,
                'Lucro/Prejuízo': lucro_prejuizo,
                'Rentabilidade (%)': rentabilidade
            })
            
    df_carteira = pd.DataFrame(carteira)
    
    if not df_carteira.empty:
        total_investido_geral = df_carteira['Total Investido'].sum()
        total_atual_geral = df_carteira['Total Atual'].sum()
        lucro_geral = total_atual_geral - total_investido_geral
        rent_geral = (lucro_geral / total_investido_geral) * 100 if total_investido_geral > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Investido", f"R$ {total_investido_geral:,.2f}")
        col2.metric("📈 Valor Atual da Carteira", f"R$ {total_atual_geral:,.2f}")
        col3.metric("📊 Lucro/Prejuízo Total", f"R$ {lucro_geral:,.2f}", delta=f"{rent_geral:.2f}%")
        col4.metric("🗂️ Qtd de Ativos", len(df_carteira))
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("### 🍰 Distribuição por Ativo")
            fig_ativos = px.pie(df_carteira, values='Total Atual', names='Ativo', hole=0.4,
                                color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_ativos, use_container_width=True)
            
        with c2:
            st.write("### 🏷️ Distribuição por Classe")
            fig_classe = px.pie(df_carteira, values='Total Atual', names='Classe', hole=0.4,
                                color_discrete_sequence=['#1f77b4', '#ff7f0e'])
            st.plotly_chart(fig_classe, use_container_width=True)
            
        st.markdown("---")
        
        st.write("### 📋 Seus Ativos Detalhados")
        st.dataframe(df_carteira.style.format({
            'Preço Médio': 'R$ {:.2f}',
            'Preço Atual': 'R$ {:.2f}',
            'Total Investido': 'R$ {:.2f}',
            'Total Atual': 'R$ {:.2f}',
            'Lucro/Prejuízo': 'R$ {:.2f}',
            'Rentabilidade (%)': '{:.2f}%'
        }), use_container_width=True, hide_index=True)
        
        with st.expander("🔍 Ver histórico de transações"):
            st.table(df_t)
else:
    st.info("👋 Sua carteira está vazia. Use o menu lateral para adicionar sua primeira compra de Ações ou FIIs!")
